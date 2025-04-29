import curses
import time
import random
import socket
import threading

BROADCAST_IP = '255.255.255.255'
JOB_RANGE = (50000, 50025)

initialPort = random.randint(JOB_RANGE[0], JOB_RANGE[1])

messages = []
lock = threading.Lock()


def findGoodPort(startPort):
    global initialPort

    currPort = startPort
    while True:
        listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen.bind(('', currPort))
        listen.settimeout(0.5)
        try:
            data, addr = listen.recvfrom(1024)
            msg, nextPort = data.decode().split(':')
            with lock:
                messages.append(f"Contract found: {msg}")
            initialPort = currPort + 1
            return int(nextPort), currPort
        except socket.timeout:
            print(currPort)
            currPort += 1
            if currPort > JOB_RANGE[1]:
                currPort = JOB_RANGE[0]
            if currPort == startPort:  # Check if we wrapped back to the start port
                with lock:
                    messages.append("No contracts available.")
                return None, currPort
            pass


def main(stdscr):
    global initialPort

    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)

    height, width = stdscr.getmaxyx()

    output_height = height - 4
    output_win = curses.newwin(output_height, width, 0, 0)
    input_win = curses.newwin(3, width, output_height, 0)

    input_buffer = ''
    cursor_visible = True
    cursor_timer = time.time()

    stdscr.nodelay(True)
    input_win.nodelay(True)

    spinner = ['|', '/', '-', '\\']
    spin_idx = 0

    while True:
        try:
            output_win.erase()
            input_win.erase()

            # Draw output window
            output_win.attron(curses.color_pair(3))
            output_win.box()
            output_win.attroff(curses.color_pair(3))

            with lock:
                for idx, line in enumerate(messages[-(output_height-3):]):
                    output_win.addstr(idx+1, 2, line[:width-4], curses.color_pair(1))

            instruction = "'s' to scan for a job, 'q' to quit"
            output_win.addstr(output_height-2, 2, instruction[:width-4], curses.color_pair(1))

            output_win.refresh()

            # Draw input window
            input_win.attron(curses.color_pair(3))
            input_win.box()
            input_win.attroff(curses.color_pair(3))

            input_win.addstr(1, 2, input_buffer[:width-4], curses.color_pair(1))

            # Blinking cursor
            if (time.time() - cursor_timer) > 0.5:
                cursor_visible = not cursor_visible
                cursor_timer = time.time()

            cursor_x = 2 + len(input_buffer)
            if cursor_visible and cursor_x < width-2:
                input_win.attron(curses.color_pair(2))
                input_win.addstr(1, cursor_x, " ")
                input_win.attroff(curses.color_pair(2))

            input_win.refresh()

            try:
                key = input_win.get_wch()
                if isinstance(key, str):
                    if key in ('\n', '\r'):
                        userInput = input_buffer.strip().lower()
                        input_buffer = ''

                        if userInput == 's':
                            # Start showing loading animation
                            loading = True
                            spin_start = time.time()
                            port = None
                            scan_finished = False
                            scan_thread = None
                            proposedPort = None

                            while loading:
                                # Animate radar
                                spin_char = spinner[spin_idx % len(spinner)]
                                spin_idx += 1

                                input_win.erase()
                                input_win.attron(curses.color_pair(3))
                                input_win.box()
                                input_win.attroff(curses.color_pair(3))
                                input_win.addstr(1, 2, f"Scanning {spin_char}", curses.color_pair(1))
                                input_win.refresh()

                                if scan_thread is None:
                                    # Try to find port, but non-blocking
                                    def try_find():
                                        nonlocal port, scan_finished, proposedPort
                                        port, proposedPort = findGoodPort(initialPort)
                                        scan_finished = True

                                    scan_thread = threading.Thread(target=try_find)
                                    scan_thread.start()

                                scan_thread.join(timeout=0.1)  # Block with a timeout

                                if scan_finished:
                                    loading = False

                            if port is None:
                                continue

                            with lock:
                                messages.append("Accept job?")

                            # Wait for yes/no input
                            decision = ''
                            loop = True
                            while loop:
                                try:
                                    # Refresh windows to show new messages
                                    output_win.erase()
                                    input_win.erase()

                                    output_win.attron(curses.color_pair(3))
                                    output_win.box()
                                    output_win.attroff(curses.color_pair(3))

                                    with lock:
                                        for idx, line in enumerate(messages[-(output_height - 3):]):
                                            output_win.addstr(idx + 1, 2, line[:width - 4], curses.color_pair(1))

                                    instruction = "'y' to accept, 'n' to decline"
                                    output_win.addstr(output_height - 2, 2, instruction[:width - 4],
                                                      curses.color_pair(1))
                                    output_win.refresh()

                                    input_win.attron(curses.color_pair(3))
                                    input_win.box()
                                    input_win.attroff(curses.color_pair(3))

                                    # Blinking cursor
                                    if (time.time() - cursor_timer) > 0.5:
                                        cursor_visible = not cursor_visible
                                        cursor_timer = time.time()

                                    cursor_x = 2 + len(input_buffer)
                                    if cursor_visible and cursor_x < width - 2:
                                        input_win.attron(curses.color_pair(2))
                                        input_win.addstr(1, cursor_x, " ")
                                        input_win.attroff(curses.color_pair(2))

                                    input_win.refresh()

                                    key = input_win.get_wch()
                                    if isinstance(key, str):
                                        if key in ('y', 'n'):
                                            decision = key
                                            input_buffer = ''
                                            loop = False

                                        elif key in ('\x7f', '\b', '\x08'):
                                            input_buffer = input_buffer[:-1]
                                        elif key.isprintable():
                                            if len(input_buffer) < width - 5:
                                                input_buffer += key
                                    elif key == curses.KEY_BACKSPACE:
                                        input_buffer = input_buffer[:-1]

                                except curses.error:
                                    pass
                                time.sleep(0.05)

                            if decision == 'y':
                                detailsSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                                detailsSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                                detailsSock.bind(('', port))
                                detailsSock.settimeout(3)

                                try:
                                    data, addr = detailsSock.recvfrom(1024)
                                    msg, completionPort = data.decode().split(':')
                                    with lock:
                                        messages.append(f"Details: {msg}")
                                except socket.timeout:
                                    with lock:
                                        messages.append("No job details received.")
                                    continue

                                # Wait for 'c'
                                loop = True
                                while loop:
                                    try:
                                        # Refresh windows to show new messages
                                        output_win.erase()
                                        input_win.erase()

                                        output_win.attron(curses.color_pair(3))
                                        output_win.box()
                                        output_win.attroff(curses.color_pair(3))

                                        with lock:
                                            for idx, line in enumerate(messages[-(output_height - 3):]):
                                                output_win.addstr(idx + 1, 2, line[:width - 4], curses.color_pair(1))

                                        instruction = "Press enter when the job is finished"
                                        output_win.addstr(output_height - 2, 2, instruction[:width - 4],
                                                          curses.color_pair(1))
                                        output_win.refresh()

                                        input_win.attron(curses.color_pair(3))
                                        input_win.box()
                                        input_win.attroff(curses.color_pair(3))

                                        # Blinking cursor
                                        if (time.time() - cursor_timer) > 0.5:
                                            cursor_visible = not cursor_visible
                                            cursor_timer = time.time()

                                        cursor_x = 2 + len(input_buffer)
                                        if cursor_visible and cursor_x < width - 2:
                                            input_win.attron(curses.color_pair(2))
                                            input_win.addstr(1, cursor_x, " ")
                                            input_win.attroff(curses.color_pair(2))

                                        input_win.refresh()

                                        key = input_win.get_wch()
                                        if isinstance(key, str):
                                            if key in ('\n', '\r'):
                                                userInput = input_buffer.strip().lower()
                                                input_buffer = ''
                                                loop = False

                                            elif key in ('\x7f', '\b', '\x08'):
                                                input_buffer = input_buffer[:-1]
                                            elif key.isprintable():
                                                if len(input_buffer) < width - 5:
                                                    input_buffer += key
                                        elif key == curses.KEY_BACKSPACE:
                                            input_buffer = input_buffer[:-1]

                                    except curses.error:
                                        pass
                                    time.sleep(0.05)


                                completionSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                                completionSock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                                completionSock.sendto("1".encode(), (BROADCAST_IP, int(completionPort)))

                                data, addr = completionSock.recvfrom(30)
                                reward = data.decode()
                                with lock:
                                    messages.append(f"${reward} wired to your account.")
                            else:
                                with lock:
                                    messages.append("Contract declined.")
                            if proposedPort is not None:
                                initialPort = proposedPort + 1
                                if initialPort > JOB_RANGE[1]:
                                    initialPort = JOB_RANGE[0]

                        elif userInput == 'q':
                            break
                        else:
                            with lock:
                                messages.append(f"Unknown command: {userInput}")

                    elif key in ('\x7f', '\b', '\x08'):
                        input_buffer = input_buffer[:-1]
                    elif key.isprintable():
                        if len(input_buffer) < width-5:
                            input_buffer += key
                elif key == curses.KEY_BACKSPACE:
                    input_buffer = input_buffer[:-1]

            except curses.error:
                pass

            time.sleep(0.05)

        except KeyboardInterrupt:
            with lock:
                messages.append("Program interrupted. Exiting...")
            break  # Gracefully exit the main loop

    # Ensure the terminal is reset properly
    curses.endwin()



if __name__ == "__main__":
    curses.wrapper(main)
