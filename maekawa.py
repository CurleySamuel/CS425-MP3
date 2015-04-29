import math
import sys
import Queue
import threading
from termcolor import colored
import time


N = 9
n = int(math.sqrt(N))
debug = False
assert math.sqrt(N)**2 == N, "N must be a square number"
assert len(sys.argv) == 5, "Require {} arguments to function, given {}".format(4,len(sys.argv)-1)
try:
    cs_int = int(sys.argv[1])
    next_req = int(sys.argv[2])
    tot_exec_time = int(sys.argv[3])
    option = int(sys.argv[4])
except ValueError:
    print "Invalid command line arguments provided. Require integers."
    sys.exit(1)


def main():
    # Each element of threads is a list with the following indices
    # 0: message queue
    # 1: list for keeping track of given vote (thread_id and tstamp)
    # 2: thread object
    global threads
    threads = []
    threads.append(None)

    # Initialize threads
    for x in range(1,N+1):
        a = []
        a.append(Queue.Queue())
        a.append(None)
        a.append(threading.Thread(target=main_thread_function, args=(x,)))
        threads.append(a)

    # Start threads
    print colored("Executing for {} seconds", "red").format(tot_exec_time)
    for x in range(1,N+1):
        threads[x][2].daemon = True
        threads[x][2].start()

    time.sleep(tot_exec_time)
    print colored("Total execution time reached. Shutting down.", "red")



def main_thread_function(thread_id):
    while 1:
        request_critical(thread_id)
        handle_messages(thread_id, request=True)
        release_critical(thread_id)
        handle_messages(thread_id, release=True)


def handle_messages(thread_id, request=False, release=False, critical=False):
    if release:
        end_time = time.time() + (next_req / 1000.0)
    elif critical:
        end_time = time.time() + (cs_int / 1000.0)
    else:
        end_time = time.time() + tot_exec_time

    granted = []
    while 1:
        msg = busy_get(thread_id, end_time)
        if msg is None:
            return
        if msg['action'] == "grant":
            granted.append(msg['src'])
            if len(granted) == 2*n - 1:
                print "{} {} {}".format(int(round(time.time() * 1000)), thread_id, ' '.join(map(str, granted)))
                return

        elif msg['action'] == "request":
            if threads[thread_id][1] is None:
                send_yes_vote(thread_id, msg)
            else:
                if threads[thread_id][1][1] < msg['tstamp']:
                    get_back_vote(thread_id, msg['src'], msg['tstamp'])
                else:
                    send_no_vote(thread_id, msg)

        elif msg['action'] == "release":
            threads[thread_id][1] = None

        elif msg['action'] == "deny":
            pass

        elif msg['action'] == "inquire":
            send_yield(thread_id, msg)

        elif msg['action'] == "yield":
            msg['src'] = msg['alternative']
            send_yes_vote(thread_id, msg)

        elif msg['action'] == "no_yield":
            msg['src'] = msg['alternative']
            send_no_vote(thread_id, msg)



def send_yes_vote(thread_id, msg):
    if debug: print colored("\t{} -> {} YES", "cyan").format(thread_id, msg['src'])
    threads[thread_id][1] = [ msg['src'], msg['tstamp'] ]
    send_msg = {
        "action": "grant",
        "src": thread_id,
        "tstamp": time.time()
    }
    threads[msg['src']][0].put(send_msg)


def send_no_vote(thread_id, msg):
    if debug: print colored("\t{} -> {} NO", "cyan").format(thread_id, msg['src'])
    send_msg = {
        "action": "deny",
        "src": thread_id,
        "tstamp": time.time()
    }
    threads[msg['src']][0].put(send_msg)


def get_back_vote(thread_id, thread, tstamp):
    if debug: print colored("\t{} -> {} INQUIRE about {}", "cyan").format(thread_id, threads[thread_id][1][0], thread)
    send_msg = {
        "action": "inquire",
        "src": thread_id,
        "alternative": thread,
        "tstamp": tstamp
    }
    threads[threads[thread_id][1][0]][0].put(send_msg)


def send_yield(thread_id, msg):
    if debug: print colored("\t{} -> {} YIELD to {}", "cyan").format(thread_id, msg['src'], msg['alternative'])
    send_msg = {
        "action": "yield",
        "src": thread_id,
        "alternative": msg['alternative'],
        "tstamp": msg['tstamp']
    }
    threads[msg['src']][0].put(send_msg)


def send_no_yield(thread_id, msg):
    if debug: print colored("\t{} -> {} NO_YIELD to {}", "cyan").format(thread_id, msg['src'], msg['alternative'])
    send_msg = {
        "action": "no_yield",
        "src": thread_id,
        "alternative": msg['alternative'],
        "tstamp": msg['tstamp']
    }
    threads[msg['src']][0].put(send_msg)


def busy_get(thread_id, end_time):
    while time.time() < end_time:
        try:
            msg = threads[thread_id][0].get_nowait()
            return msg
        except Queue.Empty:
            pass
    return None


def request_critical(thread_id):
    msg = {
        "action": "request",
        "src": thread_id,
        "tstamp": time.time()
    }
    try:
        gen = voting_set(thread_id)
        while 1:
            voting_set_member = gen.next()
            threads[voting_set_member][0].put(msg)
    except StopIteration:
        pass


def release_critical(thread_id):
    msg = {
        "action": "release",
        "src": thread_id,
        "tstamp": time.time()
    }
    try:
        gen = voting_set(thread_id)
        while 1:
            voting_set_member = gen.next()
            threads[voting_set_member][0].put(msg)
            if debug: print colored("\t{} -> {} RELEASE", "cyan").format(thread_id, voting_set_member)
    except StopIteration:
        pass


def voting_set(me):
    for x in range(1,N):
        if x % n == me % n and x != me:
            yield x
    me = me - 1
    for x in range((me/n)*n + 1, (me/n)*n + n + 1):
        yield x


if __name__ == "__main__":
    sys.exit(main())

