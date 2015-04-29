import math
import sys
import Queue
import threading
from termcolor import colored
import time


N = 9
n = int(math.sqrt(N))
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
    print colored("Total execution time reached. Shutting down.", "green")



def main_thread_function(thread_id):
    while 1:
        request_critical(thread_id)
        handle_messages(thread_id, request=True)
        release_critical(thread_id)
        handle_messages(thread_id, release=True)


def handle_messages(thread_id, request=False, release=False, critical=False):
    if request:
        grants = []
        while 1:
            last_yield = None
            if len(grants) == (2*n - 1):
                break
            msg = threads[thread_id][0].get()
            if msg['action'] == "grant":
                grants.append(msg['src'])
                if thread_id == 3:
                    print grants
            elif msg['action'] == "inquire":
                if len(grants) < (2*n - 2):
                    if last_yield is None or msg['tstamp'] < last_yield:
                        send_yield(thread_id, msg['src'], msg['to'], msg['tstamp'])
                        last_yield = msg['tstamp']
                else:
                    send_no_yield(thread_id, msg['src'], msg['to'])
            elif msg['action'] == "yield":
                msg['src'] = msg['to']
                send_yes_vote(thread_id, msg)
            else:
                handle_messages_generic(thread_id, msg)

        # We now have the critical section!
        print colored("{} Has Critical Section", "green").format(thread_id)
        return handle_messages(thread_id, critical=True)

    if release:
        end_time = time.time() + (next_req / 1000.0)
        while 1:
            msg = busy_get(thread_id, end_time)
            if msg is None:
                break
            elif msg['action'] == "yield":
                msg['src'] = msg['to']
                send_yes_vote(thread_id, msg)
            elif msg['action'] == "no_yield":
                msg['src'] = msg['to']
                send_no_vote(thread_id, msg)
            else:
                handle_messages_generic(thread_id, msg)

    if critical:
        end_time = time.time() + (cs_int / 1000.0)
        while 1:
            msg = busy_get(thread_id, end_time)
            if msg is None:
                break
            else:
                handle_messages_generic(thread_id, msg)


def handle_messages_generic(thread_id, msg):
    if msg['action'] == "request":
        if threads[thread_id][1] is None:
            send_yes_vote(thread_id, msg)
        elif threads[thread_id][1][1] > msg['tstamp']:
            get_back_vote(thread_id, threads[thread_id][1][0], msg['src'], msg['tstamp'])
        else:
            threads[thread_id][0].put(msg)
    elif msg['action'] == "release":
        if threads[thread_id][1] is not None and threads[thread_id][1][0] == msg['src']:
            threads[thread_id][1] = None
    elif msg['action'] == "inquire":
        send_no_yield(thread_id, msg['src'], msg['to'])


def send_yes_vote(thread_id, msg):
    print colored("\t{} -> {} YES", "cyan").format(thread_id, msg['src'])
    threads[thread_id][1] = [ msg['src'], msg['tstamp'] ]
    send_msg = {
        "action": "grant",
        "src": thread_id,
        "tstamp": time.time()
    }
    threads[msg['src']][0].put(send_msg)


def send_no_vote(thread_id, msg):
    print colored("\t{} -> {} NO", "cyan").format(thread_id, msg['src'])
    send_msg = {
        "action": "deny",
        "src": thread_id,
        "tstamp": time.time()
    }
    threads[msg['src']][0].put(send_msg)


def get_back_vote(thread_id, thread, to, to_tstamp):
    print colored("\t{} -> {} INQUIRE about {}", "cyan").format(thread_id, thread, to)
    msg = {
        "action": "inquire",
        "src": thread_id,
        "to": to,
        "tstamp": to_tstamp
    }
    threads[thread][0].put(msg)


def send_yield(thread_id, thread, to, to_tstamp):
    print colored("\t{} -> {} YIELD to {}", "cyan").format(thread_id, thread, to)
    msg = {
        "action": "yield",
        "src": thread_id,
        "to": to,
        "tstamp": to_tstamp
    }
    threads[thread][0].put(msg)


def send_no_yield(thread_id, thread, to):
    print colored("\t{} -> {} NO_YIELD", "cyan").format(thread_id, thread)
    msg = {
        "action": "no_yield",
        "src": thread_id,
        "to": to,
        "tstamp": time.time()
    }
    threads[thread][0].put(msg)


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
        print colored("{} Releasing Critical Section", "green").format(thread_id)
        gen = voting_set(thread_id)
        while 1:
            voting_set_member = gen.next()
            threads[voting_set_member][0].put(msg)
            print colored("\t{} -> {} RELEASE", "cyan").format(thread_id, voting_set_member)
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

