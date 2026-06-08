/*
 * ESP32 Feather V2: SPI pressure sensor + GP8403 DAC bridge
 *
 * Channel mapping:
 *   inflate  -> GP8403 channel 0
 *   deflate  -> GP8403 channel 1
 */

#include <Arduino.h>

#include <sqid.h>
#include <sender.h>
#include <receiver.h>
#include <sampleFrame.h>
#include <comMsgParser.h>

#include <SPI.h>
#include "DFRobot_GP8403.h"

const int DID = 0;			// device ID
const int PRESSURE_SID = 0;	// sensor ID for pressure sensor data
const int CHANNEL_SID = 0;	// sensor ID for channel data

const int CHAMBER_COUNT = 1;
const int CHAMBER_COUNT_MAX = 6;

// -----------------------------
// Pressure sensor SPI pins
// Kept from your tested pressure sensor sketch.
// -----------------------------

const uint8_t CS_PINS[CHAMBER_COUNT_MAX] =
	{
		12,
		27,
		33,
		15,
		32,
		14
	};

#define SCK_PIN  5
#define MISO_PIN 21
#define MOSI_PIN 19

#define MAX_OUTPUT_MV	10000

#define INFLATE_CHANNEL	0
#define DEFLATE_CHANNEL	1

// -----------------------------
// DACs
// Kept from your tested DAC sketch.
// Do not explicitly remap I2C pins here.
// -----------------------------
DFRobot_GP8403 dac58(&Wire, 0x58);
DFRobot_GP8403 dac59(&Wire, 0x59);
DFRobot_GP8403 dac5A(&Wire, 0x5A);
DFRobot_GP8403 dac5B(&Wire, 0x5B);
DFRobot_GP8403 dac5C(&Wire, 0x5C);
DFRobot_GP8403 dac5D(&Wire, 0x5D);

DFRobot_GP8403 *dacs[CHAMBER_COUNT_MAX] =
	{
		&dac58,
		&dac59,
		&dac5A,
		&dac5B,
		&dac5C,
		&dac5D
	};

const uint8_t dacAddresses[CHAMBER_COUNT_MAX] =
	{
		0x58,
		0x59,
		0x5A,
		0x5B,
		0x5C,
		0x5D
	};

// -----------------------------
// Timing
// -----------------------------
const unsigned long UPDATE_INTERVAL_MS = 5;

// -----------------------------
// Pressure calibration
// Kept from your tested SPI pressure sensor sketch.
// calibration:
//   measurement: 39
//   pressure: 1 Bar
// -----------------------------
float pressureOffset = 3440;
float pressureScale = 30.0 / 3470 * 0.026;

// -----------------------------
// Runtime variables
// -----------------------------
unsigned long lastRead = 0;
unsigned long lastCommand = 0;
bool dataReceived = false;

float currentChV[CHAMBER_COUNT];

using namespace sqid;

ComMsgParser parser;
ReceiverSerial receiver(128);

SampleFrame sensorFrame(DT_FLOAT, CHAMBER_COUNT);
SenderSerial sensorSender;

// for debugging purposes we send back the current DAC voltage
SampleFrame channelFrame(DT_FLOAT, CHAMBER_COUNT);
SenderSerial channelSender;

void enterErrorState( const char *msg )
{
	while(1)
	{
		Serial.println(msg);
		delay(5000);
	}
}

void readInput()
{
	receiver.update();
	while (receiver.getMsgQueueSize())
	{
		ComMsg msg = receiver.dequeue();

		DataType outType = DT_FLOAT;
		SampleFrame *sf = nullptr;

		switch (msg.hdr.hdr.type)
		{
		case MT_VALUE:
			sf = parser.createFrameFromSingleValue(msg.hdr.hdr, msg.data, outType);
			break;
		case MT_ARRAY:
			sf = parser.createFrameFromArray(msg.hdr.hdr, msg.data, outType);
			break;
		case MT_MATRIX:
			sf = parser.createFrameFromMatrix(msg.hdr.hdr, msg.data, outType);
			break;
		case MT_IMAGE:
			sf = parser.createFrameFromImage(msg.hdr.hdr, msg.data, outType);
			break;
		default:
			//TODO: error handling
			break;
		}

		if (!sf)
		{
			//TODO: error handling
		}
		else
		{
			lastCommand = millis();
			dataReceived = true;

			size_t width = sf->getWidth();
			size_t height = sf->getHeight();
			size_t depth = sf->getDepth();

			//TODO: respond to input data
		}

		safeDelete(sf);
	}
}

void writeValve(uint8_t id, float mV)
{
	if(id > CHAMBER_COUNT)
		return;

	int mV0 = ( mV > 0 ? clamp<float>(mV, 0, MAX_OUTPUT_MV) : 0.0f );
	int mV1 = ( mV < 0 ? clamp<float>(-mV, 0, MAX_OUTPUT_MV) : 0.0f );

	dacs[id]->setDACOutVoltage(mV0, INFLATE_CHANNEL);
	dacs[id]->setDACOutVoltage(mV1, DEFLATE_CHANNEL);

	currentChV[id] = clamp<float>(mV, -MAX_OUTPUT_MV, MAX_OUTPUT_MV);
}

/**
 * Initialize SPI communication for pressure sensor.
 * Kept from your tested pressure sensor sketch.
 */
void setupSPI()
{
	for( int i = 0; i < CHAMBER_COUNT_MAX; i++ )
	{
		pinMode(CS_PINS[i], OUTPUT);
		digitalWrite(CS_PINS[i], HIGH);
	}

	SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, -1);
	SPI.setFrequency(500000);
	SPI.setDataMode(SPI_MODE0);
}

/**
 * Read pressure from the Amphenol ELVH-100A-HAND-I-PSA4 pressure sensor.
 * Kept intentionally close to your tested pressure sensor sketch.
 */
float readPressure(uint8_t id)
{
	int raw = 0;

	uint8_t pin = CS_PINS[id];

	digitalWrite(pin, LOW);
	raw = SPI.transfer32(0xffffffff);
	digitalWrite(pin, HIGH);

	// first 2 bits are status information
	// 14 bit pressure data mapping 100 PSI
	raw = ( raw & 0x3fff0000 ) >> 16;

	return std::max(( raw - pressureOffset ) * pressureScale, 0.0f);
}

void setup()
{
	if( CHAMBER_COUNT_MAX < CHAMBER_COUNT )
		enterErrorState("chamber count exceeds maximum");

	for( int i = 0; i < CHAMBER_COUNT; i++ )
		currentChV[i] = 0.0f;

	Serial.begin(115200);
	lastRead = millis();
	lastCommand = millis();

	setupSPI();

	for (int i = 0; i < CHAMBER_COUNT; i++)
	{
		while (dacs[i]->begin())
		{
			Serial.printf("DAC %d init error", i);
			delay(1000);
		}

		dacs[i]->setDACOutRange(dacs[i]->eOutputRange10V);

		dacs[i]->setDACOutVoltage(0, 0);
		dacs[i]->setDACOutVoltage(0, 1);
	}

	if (!sensorSender.init(&sensorFrame, DID, PRESSURE_SID))
		enterErrorState("failed to init sensor sender");
	if (!channelSender.init(&channelFrame, DID, CHANNEL_SID))
		enterErrorState("failed to init channel sender");

}

void loop()
{
	readInput();

	unsigned long currentMillis = millis();

	// Read and publish pressure every 5 ms.
	if ((unsigned long)(currentMillis - lastRead) >= UPDATE_INTERVAL_MS)
	{
		lastRead += UPDATE_INTERVAL_MS;

		float *ptr = reinterpret_cast<float *>(sensorFrame.getData());
	
		for( int i = 0; i < CHAMBER_COUNT; i++ )
			*(ptr++) = readPressure(i);
		sensorSender.send();

		ptr = reinterpret_cast<float *>(channelFrame.getData());
		for( int i = 0; i < CHAMBER_COUNT; i++ )
			*(ptr++) = currentChV[i];
		channelSender.send();
	}
}