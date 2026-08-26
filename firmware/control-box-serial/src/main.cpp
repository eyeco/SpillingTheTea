/*
 * ESP32 Feather V2
 * Amphenol ELVH-030G-HAND-C-PSA4 SPI pressure sensor
 * GP8403 DAC bridge
 * 
 * Channel mapping:
 *   inflate  -> GP8403 channel 0
 *   deflate  -> GP8403 channel 1
 */

#include <Arduino.h>

//#define _NOSPI
//#define _NODAC

//#define _OSC_DEBUG

#include <sqid.h>
#include <sender.h>
#include <receiver.h>
#include <sampleFrame.h>
#include <comMsgParser.h>

#ifndef _NOSPI
#include <SPI.h>
#endif

#ifndef _NODAC
#include "DFRobot_GP8403.h"
#endif

#ifdef _OSC_DEBUG
#include <WiFi.h>
#include <OSCBundle.h>

const char *ssid = "<ENTER SSID HERE>";
const char *key = "<ENTER KEY HERE>";

WiFiUDP udp;

#define OSC_IP      "192.168.0.222"
#define OSC_PORT    6667

OSCBundle bndl;
#endif

// outgoing data
const int DID = 0;			// device ID
const int PRESSURE_SID = 0;	// sensor ID for pressure sensor data
const int CHANNEL_SID = 1;	// sensor ID for channel data

// incoming data
const int PID_DID = 1;		// PID controller's device ID
const int PID_SID = 0;		// PID controller's sensor ID

const int CHAMBER_COUNT = 5;
const int CHAMBER_COUNT_MAX = 5;

// -----------------------------
// Pressure sensor SPI pins
// Kept from your tested pressure sensor sketch.
// -----------------------------

#ifndef _NOSPI
const uint8_t CS_PINS[CHAMBER_COUNT_MAX] =
	{
		 12
		,27
		,33
		,15
		,32
		//,14
	};

#define SCK_PIN  5
#define MISO_PIN 21
#define MOSI_PIN 19
#endif


#define MAX_OUTPUT_MV	10000

#ifndef _NODAC

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
//DFRobot_GP8403 dac5D(&Wire, 0x5D);

DFRobot_GP8403 *dacs[CHAMBER_COUNT_MAX] =
	{
		 &dac58
		,&dac59
		,&dac5A
		,&dac5B
		,&dac5C
//		,&dac5D
	};

const uint8_t dacAddresses[CHAMBER_COUNT_MAX] =
	{
		 0x58
		,0x59
		,0x5A
		,0x5B
		,0x5C
//		,0x5D
	};
#endif

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
const float PRESSURE_OFFSET = 3440.0f;
const float PRESSURE_SCALE = 30.0f / 3470.0f;

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

//test
SampleFrame echoFrame(DT_FLOAT, 1);
SenderSerial echoSender;
//-----

void oscDebug( const char *msg )
{
#ifdef _OSC_DEBUG
    bndl.add("/debug").add(msg);

    udp.beginPacket(OSC_IP, OSC_PORT);
        bndl.send(udp); // send the bytes to the SLIP stream
    udp.endPacket(); // mark the end of the OSC Packet
    bndl.empty(); // empty the bundle to free room for a new one
#endif
}

void oscWarning( const char *msg )
{
#ifdef _OSC_DEBUG
    bndl.add("/warning").add(msg);

    udp.beginPacket(OSC_IP, OSC_PORT);
        bndl.send(udp); // send the bytes to the SLIP stream
    udp.endPacket(); // mark the end of the OSC Packet
    bndl.empty(); // empty the bundle to free room for a new one
#endif
}

void oscError( const char *msg )
{
#ifdef _OSC_DEBUG
    bndl.add("/error").add(msg);

    udp.beginPacket(OSC_IP, OSC_PORT);
        bndl.send(udp); // send the bytes to the SLIP stream
    udp.endPacket(); // mark the end of the OSC Packet
    bndl.empty(); // empty the bundle to free room for a new one
#endif
}

void enterErrorState( const char *msg )
{
	oscError(msg);
	while(1)
	{
		Serial.println(msg);
		delay(5000);
	}
}

void writeValve(uint8_t id, float mV)
{
	if(id > CHAMBER_COUNT)
		return;

#ifndef _NODAC
	int mV0 = ( mV > 0 ? clamp<float>(mV, 0, MAX_OUTPUT_MV) : 0.0f );
	int mV1 = ( mV < 0 ? clamp<float>(-mV, 0, MAX_OUTPUT_MV) : 0.0f );
	
	dacs[id]->setDACOutVoltage(mV0, INFLATE_CHANNEL);
	dacs[id]->setDACOutVoltage(mV1, DEFLATE_CHANNEL);
#endif

	currentChV[id] = clamp<float>(mV, -MAX_OUTPUT_MV, MAX_OUTPUT_MV) * 0.001f;
}

void readInput()
{
	receiver.update();
	while (receiver.getMsgQueueSize())
	{
		ComMsg msg = receiver.dequeue();

		DataType outType = DT_FLOAT;
		SampleFrame *sf = nullptr;

		if (msg.hdr.hdr.deviceID == PID_DID && msg.hdr.hdr.sensorID == PID_SID)
		{
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
		}

		safeDeleteArray( msg.data );

		if (!sf)
		{
			oscError("decoding commsg failed");
			//TODO: error handling
		}
		else
		{
			lastCommand = millis();
			dataReceived = true;

			size_t width = sf->getWidth();
			size_t height = sf->getHeight();
			size_t depth = sf->getDepth();
			size_t size = width * height * depth;

			//TODO: respond to input data
			const float *ptr = reinterpret_cast<const float*>(sf->getData());
			float *ptr2 = reinterpret_cast<float*>(echoFrame.getData());
			for( int i = 0; i < size; i++ )
			{
				writeValve(i, ptr[i] * 1000.0f);
				ptr2[i] = ptr[i];
			}

			echoSender.send();
		}

		safeDelete(sf);
	}
}

#ifndef _NOSPI
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

	return std::max(( raw - PRESSURE_OFFSET ) * PRESSURE_SCALE, 0.0f);
}
#endif

void setup()
{
	if( CHAMBER_COUNT_MAX < CHAMBER_COUNT )
		enterErrorState("chamber count exceeds maximum");

	for( int i = 0; i < CHAMBER_COUNT; i++ )
		currentChV[i] = 0.0f;

	Serial.begin(115200);
    while (!Serial); // wait for serial port to connect. Needed for Leonardo only

#ifdef _OSC_DEBUG
	int status = WL_IDLE_STATUS; 

	WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, key);
    Serial.println("\nConnecting to WiFi Network ..");

    while(WiFi.status() != WL_CONNECTED){
        Serial.print(".");
        delay(100);
    }

    Serial.println("\nConnected to the WiFi network");
    Serial.print("Local ESP32 IP: ");
    Serial.println(WiFi.localIP());
#endif

	lastRead = millis();
	lastCommand = millis();

#ifndef _NOSPI
	setupSPI();
#endif

#ifndef _NODAC
	for (int i = 0; i < CHAMBER_COUNT; i++)
	{
		while (dacs[i]->begin())
		{
			Serial.printf("DAC %d init error\n", i);
			delay(1000);
		}

		dacs[i]->setDACOutRange(dacs[i]->eOutputRange10V);

		dacs[i]->setDACOutVoltage(0, 0);
		dacs[i]->setDACOutVoltage(0, 1);
	}
#endif

	Serial.println("initing sensorsender");
	
	if (!sensorSender.init(&sensorFrame, DID, PRESSURE_SID))
		enterErrorState("failed to init sensor sender");
	Serial.println("initing channelsender");
	if (!channelSender.init(&channelFrame, DID, CHANNEL_SID))
		enterErrorState("failed to init channel sender");
	
	//test
	Serial.println("initing echosender");
	echoFrame.set<float>( 0.0f );
	if (!echoSender.init(&echoFrame, DID, 254))
		enterErrorState("failed to init echo sender");
	//-----

	Serial.println("initing DONE");
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
#ifndef _NOSPI
		for( int i = 0; i < CHAMBER_COUNT; i++ )
			*(ptr++) = readPressure(i);
#endif
		sensorSender.send();

		ptr = reinterpret_cast<float *>(channelFrame.getData());
		for( int i = 0; i < CHAMBER_COUNT; i++ )
			*(ptr++) = currentChV[i];
		channelSender.send();
	}

	delay(1);
}