#ifndef SERIALHANDLER_H
#define SERIALHANDLER_H
#include <stddef.h>

template<typename T, size_t N>
class RingBuffer {
public:
    static_assert(N > 0, "RingBuffer size must be >0");

    RingBuffer(): head(0), tail(0), count(0) {}

    // status
    bool isEmpty() const          { return count == 0; }
    bool isFull() const           { return count == N; }
    size_t available() const      { return count; }
    size_t freeSpace() const      { return N - count; }

    // read up to 'len' bytes from serial into buffer, returns bytes read
    size_t bulkRead(Stream& serial, size_t len) {
        size_t toRead = min(len, freeSpace());
        if (!toRead) return 0;

        size_t total = 0;
        // first chunk (up to end of array)
        size_t first = min(toRead, N - head);
        size_t got1  = serial.readBytes(reinterpret_cast<uint8_t*>(buf + head), first);
        head = (head + got1) % N;
        count += got1;
        total += got1;

        // wrap‑around remainder
        size_t rem = toRead - got1;
        if (rem) {
            size_t got2 = serial.readBytes(reinterpret_cast<uint8_t*>(buf + head), rem);
            head = (head + got2) % N;
            count += got2;
            total += got2;
        }
        return total;
    }

    // pop up to 'len' items into dest[], returns items written
    size_t bulkWrite(T* dest, size_t len) {
        size_t toWrite = min(len, available());
        if (!toWrite) return 0;

        size_t total = 0;
        // first chunk
        size_t first = min(toWrite, N - tail);
        memcpy(dest, buf + tail, first * sizeof(T));
        tail  = (tail  + first) % N;
        count -= first;
        total += first;

        // wrap‑around remainder
        size_t rem = toWrite - first;
        if (rem) {
            memcpy(dest + first, buf + tail, rem * sizeof(T));
            tail  = (tail  + rem) % N;
            count -= rem;
            total += rem;
        }
        return total;
    }

    // byte‑wise pull (returns false if empty)
    bool get(T& out) {
        if (isEmpty()) return false;
        out = buf[tail];
        tail = (tail + 1) % N;
        --count;
        return true;
    }

private:
    T      buf[N];
    size_t head, tail, count;
};

#endif // SERIALHANDLER_H
