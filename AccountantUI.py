import curses
import time
import threading
import socket
import random

# Globals used by networking
BROADCAST_IP = '255.255.255.255'
JOB_RANGE = (50000, 50025)
DETAIL_RANGE = (50100, 50125)
COMPLETION_RANGE = (50200, 50225)
takenPorts = []
jobs = {
    'JohnWick': {
        'details': "The lottery just went up...",
        'reward': 40000000
    },
    'MrNobody': {
        'details': "You pay for the service",
        'reward': 7000000
    },
    'Killa Harken': {
        'details': "Five of a kind",
        'reward': 22222
    },
    'Caine': {
        'details': "I will serve, I will be of service",
        'reward': 0
    }
}
lock = threading.Lock()


def findPorts():
    jobPort = random.randint(*JOB_RANGE)
    while jobPort in takenPorts:
        jobPort = random.randint(*JOB_RANGE)
    takenPorts.append(jobPort)

    detailPort = random.randint(*DETAIL_RANGE)
    while detailPort in takenPorts:
        detailPort = random.randint(*DETAIL_RANGE)
    takenPorts.append(detailPort)

    completionPort = random.randint(*COMPLETION_RANGE)
    while completionPort in takenPorts:
        completionPort = random.randint(*COMPLETION_RANGE)
    takenPorts.append(completionPort)

    return [jobPort, detailPort, completionPort]


def handleJob(job, foundPorts, messages, lock):
    currJob = jobs[job]

    jobSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    jobSock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    detailSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    detailSock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    completionSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    completionSock.bind(('', foundPorts[2]))
    completionSock.settimeout(0.5)

    while True:
        jobSock.sendto(f"{job}:{foundPorts[1]}".encode(), (BROADCAST_IP, foundPorts[0]))
        detailSock.sendto(f"{currJob['details']}:{foundPorts[2]}".encode(), (BROADCAST_IP, foundPorts[1]))
        try:
            data, addr = completionSock.recvfrom(1024)
            if data.decode() == "1":
                completionSock.sendto(str(currJob['reward']).encode(), addr)
                break
        except socket.timeout:
            pass

    takenPorts.remove(foundPorts[0])
    takenPorts.remove(foundPorts[1])
    takenPorts.remove(foundPorts[2])
    del jobs[job]

    with lock:
        messages.append(f"{job} closed")


messages = []

class ContractUI:
    def __init__(self, stdscr, messages):
        self.stdscr = stdscr
        self.messages = messages
        self.input_buffer = ''
        self.cursor_visible = True
        self.cursor_timer = time.time()
        self.flicker = False
        self.last_flicker = time.time()

        self.height, self.width = stdscr.getmaxyx()
        self.output_height = self.height - 4
        self.output_win = curses.newwin(self.output_height, self.width, 0, 0)
        self.input_win = curses.newwin(3, self.width, self.output_height, 0)

        self.output_win.nodelay(True)
        self.input_win.nodelay(True)

        curses.curs_set(0)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)

    def draw_ui(self, instruction=""):
        # Update flicker every ~0.25s
        if time.time() - self.last_flicker > 0.25:
            self.flicker = random.choice([True, False, False])
            self.last_flicker = time.time()

        self.output_win.erase()
        self.input_win.erase()

        if self.flicker:
            attr = curses.color_pair(1) | curses.A_BOLD
        else:
            attr = curses.color_pair(1)

        self.output_win.attron(curses.color_pair(3))
        self.output_win.box()
        self.output_win.attroff(curses.color_pair(3))

        with lock:
            for idx, line in enumerate(self.messages[-(self.output_height - 3):]):
                self.output_win.addstr(idx + 1, 2, line[:self.width - 4], attr)

        self.output_win.addstr(self.output_height - 2, 2, instruction[:self.width - 4], attr)
        self.output_win.refresh()

        self.input_win.attron(curses.color_pair(3))
        self.input_win.box()
        self.input_win.attroff(curses.color_pair(3))

        self.input_win.addstr(1, 2, self.input_buffer[:self.width - 4], curses.color_pair(1))

        if (time.time() - self.cursor_timer) > 0.5:
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = time.time()

        cursor_x = 2 + len(self.input_buffer)
        if self.cursor_visible and cursor_x < self.width - 2:
            self.input_win.attron(curses.color_pair(2))
            self.input_win.addstr(1, cursor_x, " ")
            self.input_win.attroff(curses.color_pair(2))

        self.input_win.refresh()

    def get_input(self, prompt):
        self.input_buffer = ''
        while True:
            self.draw_ui(prompt)
            try:
                key = self.input_win.get_wch()
                if isinstance(key, str):
                    if key in ('\n', '\r'):
                        return self.input_buffer.strip()
                    elif key in ('\x7f', '\b', '\x08'):
                        self.input_buffer = self.input_buffer[:-1]
                    elif key.isprintable() and len(self.input_buffer) < (self.width - 5):
                        self.input_buffer += key
                elif key == curses.KEY_BACKSPACE:
                    self.input_buffer = self.input_buffer[:-1]
            except curses.error:
                pass
            time.sleep(0.05)

    def run(self):
        while True:
            self.draw_ui("'open' a contract or 'hangup'")
            try:
                key = self.input_win.get_wch()
                if isinstance(key, str):
                    if key in ('\n', '\r'):
                        command = self.input_buffer.strip().lower()
                        self.input_buffer = ''

                        if command == "open":
                            name = self.get_input("Enter Contract Name")
                            self.input_buffer = ''
                            details = self.get_input("Enter Contract Details")
                            self.input_buffer = ''
                            reward = self.get_input("Enter Contract Reward")
                            self.input_buffer = ''

                            if name in jobs:
                                with lock:
                                    messages.append(f"{name} is already open.")
                            else:
                                jobs[name] = {
                                    'details': details,
                                    'reward': int(reward)
                                }
                                with lock:
                                    messages.append(f"{name} opening at {jobs[name]['reward']}")
                                foundPorts = findPorts()
                                threading.Thread(target=handleJob, args=(name, foundPorts, messages, lock), daemon=True).start()

                        elif command == "hangup":
                            with lock:
                                messages.append("Have a nice day.")
                            break
                        else:
                            with lock:
                                messages.append(f"Unknown command: {command}")
                    elif key in ('\x7f', '\b', '\x08'):
                        self.input_buffer = self.input_buffer[:-1]
                    elif key.isprintable():
                        if len(self.input_buffer) < (self.width - 5):
                            self.input_buffer += key
                elif key == curses.KEY_BACKSPACE:
                    self.input_buffer = self.input_buffer[:-1]
            except curses.error:
                pass
            time.sleep(0.05)


def start_ui(stdscr):
    ui = ContractUI(stdscr, messages)
    ui.run()

if __name__ == "__main__":
    for job in list(jobs.keys()):
        foundPorts = findPorts()
        threading.Thread(target=handleJob, args=(job, foundPorts, messages, lock), daemon=True).start()

    curses.wrapper(lambda stdscr: ContractUI(stdscr, messages).run())

