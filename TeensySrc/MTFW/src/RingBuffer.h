#ifndef RING_BUFFER
#define RING_BUFFER
#include <stddef.h>

template <typename T, size_t SIZE>
class RingBuffer
{
private:
    T *buffer;
    size_t head;
    size_t tail;
    size_t count;
public:
    RingBuffer(T *externalBuffer) : buffer(externalBuffer), head(0), tail(0), count(0) {}
    const T &operator[](size_t index) const
    {
        size_t ringIndex = (tail + index) % SIZE;
        return buffer[ringIndex];
    }
    bool push(const T &item)
    {
        if (count < SIZE)
        {
            buffer[head] = item;
            head = (head + 1) % SIZE;
            count++;
            return true;
        }
        return false; // Buffer is full
    }

    bool pop(T &item)
    {
        if (count > 0)
        {
            item = buffer[tail];
            tail = (tail + 1) % SIZE;
            count--;
            return true;
        }
        return false; // Buffer is empty
    }
    bool popUntil(const T &target)
    {
        while (count > 0)
        {
            T currentItem = buffer[tail];
            tail = (tail + 1) % SIZE;
            count--;
            
            if (currentItem == target)
            {
                return true; // Found and removed target
            }
        }
        return false; // Target not found
    }
    size_t size() const
    {
        return count;
    }

    bool isEmpty() const
    {
        return count == 0;
    }

    bool isFull() const
    {
        return count == SIZE;
    }

    size_t readBytes(uint8_t *dest, size_t n)
    {
        if (n == 0 || count == 0 || dest == nullptr)
            return 0;
        size_t toRead = (n < count) ? n : count;
        size_t tailToEnd = SIZE - tail;
        size_t chunk1 = (toRead < tailToEnd) ? toRead : tailToEnd;
        memcpy(dest, &buffer[tail], chunk1 * sizeof(T));
        tail = (tail + chunk1) % SIZE;
        count -= chunk1;
        if (chunk1 == toRead)
            return chunk1;
        size_t chunk2 = toRead - chunk1;
        memcpy(dest + chunk1, &buffer[tail], chunk2 * sizeof(T));
        tail = (tail + chunk2) % SIZE;
        count -= chunk2;
        return chunk1 + chunk2;
    }
    size_t writeBytes(const uint8_t *src, size_t n)
    {
        if (n == 0 || src == nullptr)
            return 0;
        size_t space = SIZE - count;
        if (space == 0)
            return 0;
        size_t toWrite = (n < space) ? n : space;
        size_t headToEnd = SIZE - head;
        size_t chunk1 = (toWrite < headToEnd) ? toWrite : headToEnd;
        memcpy(&buffer[head], src, chunk1 * sizeof(T));
        head = (head + chunk1) % SIZE;
        count += chunk1;
        if (chunk1 == toWrite)
            return chunk1;
        size_t chunk2 = toWrite - chunk1;
        memcpy(&buffer[head], src + chunk1, chunk2 * sizeof(T));
        head = (head + chunk2) % SIZE;
        count += chunk2;
        return chunk1 + chunk2;
    }
    template <typename StreamType>
    size_t readStream(StreamType &serial)
    {
        size_t avail = serial.available();
        size_t space = SIZE - count;
        if (avail == 0 || space == 0)
            return 0;

        size_t toRead = (avail < space) ? avail : space;

        size_t headToEnd = SIZE - head;
        size_t chunk1 = (toRead < headToEnd) ? toRead : headToEnd;
        size_t n1 = serial.readBytes(reinterpret_cast<char *>(buffer + head), chunk1);
        count += n1;

        head = (head + n1) % SIZE;
        if (n1 < chunk1 || n1 == toRead)
            return n1;
        size_t chunk2 = toRead - n1;
        size_t n2 = serial.readBytes(reinterpret_cast<char *>(buffer + head), chunk2);
        count += n2;
        head = (head + n2) % SIZE;
        return n1 + n2;
    }


};

#endif // RING_BUFFER