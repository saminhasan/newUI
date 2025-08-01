from threading import Thread, Event
import time

running = True
event = Event()
read = Event()


def foo(running, event, read):
    while running:
        print(f"IN :{running=}, {event.is_set()=}")
        event.wait()
        while running and event.is_set():
            print(f"IN :{running=}, {event.is_set()=}")
            read.wait()


if __name__ == "__main__":

    # Create an Event object

    # Start a thread that will wait for the event
    thread = Thread(target=foo, args=(running, event, read), daemon=True)
    print(f"OUT:{running=}, {event.is_set()=}")

    thread.start()
    time.sleep(2)
    print(f"OUT:{running=}, {event.is_set()=}")

    event.set()  # This will unblock the thread
    time.sleep(2)  # Let the thread run for a while
    running = False  # Stop the thread
    event.clear()
    print(f"OUT:{running=}, {event.is_set()=}")
    read.set()
    thread.join()  # Wait for the thread to finish
    print("Thread has finished execution.")
