#ifndef DELF_H
#define DELF_H
#include <FlexCAN_T4.h>
#include "motctrl_prot.h"
#include "messages.h"
#include <Bounce2.h>

struct __attribute__((packed)) Feedback
{
    uint8_t axisId;                   // 1
    uint8_t mode;                     // 1
    uint8_t armed;                    // 1
    uint8_t calibrated;               // 1
    float setPoint;                   // 4
    uint32_t tSend;                   // 4
    uint32_t tRecv;                   // 4
    uint8_t sent[MOTCTRL_FRAME_SIZE]; // 8
    uint8_t recv[MOTCTRL_FRAME_SIZE]; // 8
};
template <typename StreamType>
void sendFeedback(StreamType &serial, const Feedback &feedback)
{
    static uint32_t feedbackCounter = 0;
    sendPacket(serial, sizeof(feedback), feedbackCounter, NODE_ID_PC, msgID::FEEDBACK, reinterpret_cast<const uint8_t *>(&feedback));
    feedbackCounter++;
}
class Axis
{
public:
    uint8_t axisId;
    uint8_t startCmd[MOTCTRL_FRAME_SIZE];
    uint8_t stopCmd[MOTCTRL_FRAME_SIZE];
    Feedback feedback = {0};
    volatile uint32_t msgOut = 0;
    volatile uint32_t msgIn = 0;
    volatile uint32_t tSend = 0;
    volatile uint32_t tRecv = 0;
    volatile float setPoint = 0.0f;
    volatile uint8_t sendBuffer[MOTCTRL_FRAME_SIZE] = {0};
    volatile uint8_t recvBuffer[MOTCTRL_FRAME_SIZE] = {0};

    volatile bool newCanMessage = false;
    float theta, omega, tau;
    volatile float p, v, t;
    static constexpr float dTheta = 5e-2; // rad
    static constexpr float D90 = M_PI / 2;      // rad
    static constexpr float proxPos = 0.0f;      // rad
    //--------------------------------------------------------
    int proxPin = -1;
    int dir = 0;
    uint8_t cStage = 255;
    volatile float angle1 = 0.0f;
    volatile float angle2 = 0.0f;
    volatile float midPoint = 0.0f;
    volatile float offset = 0.0f;
    Bounce bounce = Bounce();
    volatile bool armed = false;
    volatile bool calibrated = false;
    volatile bool doCalibration = false;
    volatile uint8_t mode = 0;
    volatile float vLim = 1.0f;
    //--------------------------------------------------------
    volatile float P = 5.0f;
    volatile float D = 1.0f;
    Axis(uint8_t id) : axisId(id)
    {
        feedback.axisId = id;
        MCReqStartMotor(startCmd);
        MCReqStopMotor(stopCmd);
        dir = 1 - 2 * (id & 1);
        proxPin = (dir == -1) ? 38 : 2;
        bounce.attach(proxPin, INPUT_PULLUP);
        bounce.interval(1);

    }
    void init()
    {
        logInfo(Serial, "Initializing Axis %d (dir=%d | proxPin=%d)\n", axisId, dir, proxPin);
    }
    void update()
    {
        static uint8_t pStage = 0;
        static uint32_t waitCounter = 0;
        if (doCalibration && !calibrated)
        {
            bounce.update();
            if(pStage != cStage) {
                 pStage = cStage;
                logInfo(Serial, "Calibrating Axis %d (stage=%d | u:%f : y:%f |)\n", axisId, pStage, setPoint, theta);
            }
            bool proxOut = bounce.read();
            switch (cStage)
            {

            case 0:
                if (!proxOut)
                    setPoint = theta + dTheta*dir;
                else
                    cStage++;
                break;
            case 1:
                if(waitCounter++ < 5000) // wait 1 second
                    break;
                else
                {
                    waitCounter = 0;
                    cStage++;
                }
                break;
            case 2:
                if (proxOut)
                    setPoint = theta + dTheta*dir;
                else
                {
                    angle1 = theta;
                    cStage++;
                }
                break;
            case 3:
                if (!proxOut)
                    setPoint = theta -(dir * dTheta);
                else
                    cStage++;
                break;
            case 4:
                if (proxOut)
                    setPoint = theta -(dir * dTheta);
                else
                {
                    angle2 = theta;
                    cStage++;
                }
                break;
            case 5:
                    offset = (angle1 + angle2) / 2.0f;
                    // offset = atan2f(sinf(angle1)+sinf(angle2), cosf(angle1)+cosf(angle2));
                    setPoint  += 0.01 * (offset - setPoint);
                    if (fabs(offset - setPoint) < 0.001)
                        cStage++;
                    break;
            case 6:
                    calibrated = true;
                    doCalibration = false;
                    cStage = 0;
                break;
            case 255:
                setPoint = theta;
                cStage++;
                break;
            default:
                break;
            }
        }
        if (armed)
            setPosition_PD();
        return;
    }

    void tick()
    {
        if (!newCanMessage)
            return;
        theta = p;
        omega = v;
        tau = t;
        feedback.armed = armed;
        feedback.calibrated = calibrated;
        feedback.mode = mode;
        feedback.setPoint = setPoint;
        feedback.tSend = tSend;
        feedback.tRecv = tRecv;
        for (size_t i = 0; i < MOTCTRL_FRAME_SIZE; i++)
        {
            feedback.sent[i] = sendBuffer[i];
            feedback.recv[i] = recvBuffer[i];
        }
        sendFeedback(Serial, feedback);
        newCanMessage = false;
    }
    void setGain()
    {
        P = 100.0f;
        vLim = 12.0f;
        mode = 1;
        return;
    }

    void resetGain()
    {
        P = 5.0f;
        vLim = 0.33f;
        mode = 0;
        return;
    }

    void setPositionSetpoint(float position)
    {
        setPoint = bodyToMotorFrame(constrain(position, -D90, D90));
    }

    void calibrate()
    {
        if (!calibrated)
            doCalibration = true;
        return;
    }

    void enable()
    {
        if (armed)
            return;
        canSend(startCmd);
    }

    void setPosition()
    {
        uint8_t buf[MOTCTRL_FRAME_SIZE];
        MCReqPositionControl(buf, setPoint, 0);
        canSend(buf);
    }

    void setPosition_PD()
    {
        setVelocity(((setPoint - theta) * P) - (omega * D));
    }
    void setVelocity(float velocity)
    {
        uint8_t buf[MOTCTRL_FRAME_SIZE];
        velocity = constrain(velocity, -vLim, vLim);
        MCReqSpeedControl(buf, velocity, 0);
        canSend(buf);
    }

    void disable()
    {
        canSend(stopCmd);
    }

    void canSend(const uint8_t *reqBuf)
    {
        CAN_message_t msg;
        msg.id = 0x01;
        msg.len = MOTCTRL_FRAME_SIZE;
        memcpy(msg.buf, reqBuf, MOTCTRL_FRAME_SIZE);
        // select the CAN bus
        switch (dir)
        {
        case -1:
            Can1.write(msg);
            break;
        case 1:
            Can2.write(msg);
            break;
        default:
            break;
        }
        tSend = micros();
        for (size_t i = 0; i < MOTCTRL_FRAME_SIZE; i++)
            sendBuffer[i] = reqBuf[i];
        msgOut++;
    }
    void canRecv(const CAN_message_t &msg)
    {
        uint8_t buf[MOTCTRL_FRAME_SIZE];
        float pos, vel, trq;
        int8_t temperature;
        memcpy(buf, msg.buf, MOTCTRL_FRAME_SIZE);
        tRecv = micros();
        for (size_t i = 0; i < MOTCTRL_FRAME_SIZE; i++)
            recvBuffer[i] = buf[i];
        msgIn++;
        newCanMessage = true;

        switch (buf[1])
        {
        case MOTCTRL_RES_SUCCESS:
            switch (buf[0])
            {
            case MOTCTRL_CMD_START_MOTOR:
                armed = true;
                setVelocity(0.0f);
                // setPositionSetpoint(0.0f);
                break;
            case MOTCTRL_CMD_STOP_MOTOR:
                armed = false;
                break;
            case MOTCTRL_CMD_POSITION_CONTROL:
            case MOTCTRL_CMD_SPEED_CONTROL:
            case MOTCTRL_CMD_TORQUE_CONTROL:
                MCResControl(buf, &temperature, &pos, &vel, &trq);
                p = pos;
                v = vel;
                t = trq;
                // logInfo(Serial, "AXIS %d(armed=%d | position=%f | velocity=%f | torque=%f)\n", axisId, armed, pos, vel, trq);
                break;
            default:
                logInfo(Serial, "Unhandled reply : 0x%02X", buf[0]); // must log error
                break;
            }
            break;
        case MOTCTRL_RES_FAIL:
        case MOTCTRL_RES_FAIL_UNKNOWN_CMD:
        case MOTCTRL_RES_FAIL_UNKNOWN_ID:
        case MOTCTRL_RES_FAIL_RO_REG:
        case MOTCTRL_RES_FAIL_UNKNOWN_REG:
        case MOTCTRL_RES_FAIL_STR_FORMAT:
        case MOTCTRL_RES_FAIL_DATA_FORMAT:
        case MOTCTRL_RES_FAIL_WO_REG:
        case MOTCTRL_RES_FAIL_NOT_CONNECTED:
        default:
            logInfo(Serial, "MOTOR ERROR : 0x%02X", buf[0]); // must log error
            break;
        }
    }
    float motorToBodyFrame(float X_motor)
    {
        return (X_motor - offset) / dir;
    }
    float bodyToMotorFrame(float rad)
    {
        return (rad * dir) + offset;
    }
};

#endif // DELF_H