import socket
import threading
import random

# Broadcast Address
BROADCAST_IP = '<broadcast>'

# Port range for initial job details
JOB_RANGE = (50000, 50025)

# Port range for full job details
DETAIL_RANGE = (50100, 50125)

# Port range for job completions
COMPLETION_RANGE = (50200, 50225)

# List of taken ports
takenPorts = []

# Dict of jobs
jobs = {
    'JohnWick': {
        'details': "Details about JohnWick job",
        'reward': 1000000
    }
}

#### Helper Functions ####

def findPorts():
    #return a port for each range

    # JOB_RANGE
    #find random port in range
    #check if taken, if not, take it
    jobPort = random.randint(JOB_RANGE[0], JOB_RANGE[1])
    while jobPort in takenPorts:
        jobPort = random.randint(JOB_RANGE[0], JOB_RANGE[1])
    takenPorts.append(jobPort)

    # DETAIL_RANGE
    detailsPort = random.randint(DETAIL_RANGE[0], DETAIL_RANGE[1])
    while detailsPort in takenPorts:
        detailsPort = random.randint(DETAIL_RANGE[0], DETAIL_RANGE[1])
    takenPorts.append(detailsPort)

    # COMPLETION_RANGE
    completionPort = random.randint(COMPLETION_RANGE[0], COMPLETION_RANGE[1])
    while completionPort in takenPorts:
        completionPort = random.randint(COMPLETION_RANGE[0], COMPLETION_RANGE[1])
    takenPorts.append(completionPort)

    return [jobPort, detailsPort, completionPort]

#### THREADS ####

def handleJob(job, foundPorts):
    # Broadcast job, details
    # listen on completion port
    # until we hear back on completion port, keep broadcasting

    currJob = jobs[job]

    jobSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    jobSock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    detailSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    detailSock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    completionSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    completionSock.bind(('', foundPorts[2]))
    completionSock.settimeout(0.2)

    while True:
        jobSock.sendto(f"{job}:{foundPorts[1]}".encode(), (BROADCAST_IP, foundPorts[0]))
        detailSock.sendto(f"{currJob['details']}:{foundPorts[2]}".encode(), (BROADCAST_IP, foundPorts[1]))

        try:
            data, addr = completionSock.recvfrom(1024)
            if data.decode() == "1":
                # send reward back to sender
                completionSock.sendto(f"{currJob['reward']}".encode(), addr)
                break
        except socket.timeout:
            pass

    takenPorts.remove(foundPorts[0])
    takenPorts.remove(foundPorts[1])
    takenPorts.remove(foundPorts[2])
    del jobs[job]

    print(f"\n{job} closed", flush=True)
    return

### MAIN ####
# Set up a thread for each job
for job in jobs:
    # Find ports for the job first
    foundPorts = findPorts()
    threading.Thread(target=handleJob, args=(job, foundPorts), daemon=True).start()

while True:
    userInput = input("'open' a contract or 'hangup': ").lower()

    if userInput == "open":
        contract = input("Contract name? ")
        if contract in jobs:
            print(f"{contract} is already open.")
        else:
            jobs[contract] = {
                'details': input("Specifics? "),
                'reward': int(input("Enter reward amount: "))
            }
            print(f"{contract} opening at {jobs[contract]['reward']}")
            foundPorts = findPorts()
            threading.Thread(target=handleJob, args=(contract, foundPorts)).start()

    elif userInput == "hangup":
        print("Have a nice day.")
        break