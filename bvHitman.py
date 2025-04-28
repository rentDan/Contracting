import random
import socket

# Broadcast Address
BROADCAST_IP = '<broadcast>'

# Port range for initial job details
JOB_RANGE = (50000, 50025)

def findGoodPort(initialPort = None):

    #If no port, start at a random port
    if initialPort is None:
        initialPort = random.randint(JOB_RANGE[0], JOB_RANGE[1])

    currPort = initialPort
    # Continue forward until a good port is found
    while True:

        listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen.bind(('', currPort))
        listen.settimeout(0.5)
        try:
            data, addr = listen.recvfrom(1024)
            msg, nextPort = data.decode().split(':')
            print(f"{msg}")
            return int(nextPort)
        except socket.timeout:
            currPort += 1
            if currPort > JOB_RANGE[1]:
                currPort = JOB_RANGE[0]
            if currPort == initialPort:
                print("No contracts available")
                return None
            pass

while True:
    # The user will be able to scan for a job or quit the program
    userInput = input("'s' to scan for a job, 'q' to quit: ").lower()

    # If scanning
    if userInput == 's':
        # Find a port broadcasting a job
        port = findGoodPort(random.randint(JOB_RANGE[0], JOB_RANGE[1]))

        if port is None:
            continue

        # Ask the user if they accept the job
        decision = input("Accept job? (y/n): ").lower()

        # If they accept,
        if decision == 'y':
            # Use the port received to get the job details
            # and the port for job completion
            detailsSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            detailsSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            detailsSock.bind(('', port))
            detailsSock.settimeout(3)

            try:
                data, addr = detailsSock.recvfrom(1024)
                msg, completionPort = data.decode().split(':')
                print(f"{msg}")
            except socket.timeout:
                print("No job details received")
                continue

            # wait for the user to complete the job (enter anything)
            input("Press enter when done")

            # Send the job completion message to the port
            completionSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            completionSock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            completionSock.sendto("1".encode(), (BROADCAST_IP, int(completionPort)))

            # Receive the reward from the port
            data, add = completionSock.recvfrom(30)
            reward = data.decode()
            print(f"Reward: {reward}")

        # If they don't accept, continue
        elif decision == 'n':
            continue

    # If quitting
    elif userInput == 'q':
        break