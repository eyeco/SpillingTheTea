#include <Arduino.h>
#include <CD74HC4067.h>

#include <sqid.h>
#include <sender.h>
#include <sampleFrame.h>

/*
                  +3.3V (Vpp)
                    │
                [ R_ref ]
                    │
  ESP32 ADC <───────┴────── [ SIG Pin ] 
                                │
                        ┌───────┴─────────────┐  <-- CD74HC4067 MUX
                        │  CH0  CH1  CH2  ... │
                        └─┬─────┬─────┬─────┬─┘
                          │     │     │     │
                        [FSR] [FSR] [FSR]  ...
                          │     │     │     |
                         GND   GND   GND   GND
 */

const int SIG_PIN = A2;

const int MUX_S0 = 16;
const int MUX_S1 = 19;
const int MUX_S2 = 18;
const int MUX_S3 = 5;

#if defined(ESP32)
  // ESP32 defaults to 12-bit (0 - 4095)
  const int ADC_RES = 12;
#elif defined(__AVR__)
  // Classic Arduino Uno/Nano/Mega are 10-bit (0 - 1023)
  const int ADC_RES = 10; 
#elif defined(ADC_RESOLUTION)
  // Fallback for SAMD, STM32, or Teensy boards that actually define it
  const int ADC_RES = ADC_RESOLUTION;
#else
  // Ultimate safety fallback
  const int ADC_RES = 10; 
#endif

const int MAX_ADC_VALUE = (0x01 << ADC_RES) - 1;

const int DEVICE_ID = 0;
const int SENSOR_ID = 0;

const int BUTTON_NUM = 12;

const int TARGET_FPS = 100;
const int TARGET_US = 1000000 / TARGET_FPS;

CD74HC4067 mux( MUX_S0, MUX_S1, MUX_S2, MUX_S3 );

using namespace sqid;

SampleFrame buttonFrame( DT_FLOAT, BUTTON_NUM );
SenderSerial buttonSender;

float multisample( uint8_t pin, int samples )
{
	int sum = 0;
	for( int i = 0; i < samples; i++ )
		sum += analogRead(pin);
	return (float)sum / samples;
}

void setup()
{
	Serial.begin(115200);

	if (!buttonSender.init(&buttonFrame, DEVICE_ID, SENSOR_ID))
		Serial.println("failed to init button sender");
}

void loop()
{
	unsigned long usStart = micros();

	// update array data
	float *ptr = reinterpret_cast<float *>(buttonFrame.getData());

	for (int i = 0; i < BUTTON_NUM; i++)
	{
		mux.channel(i);
		delayMicroseconds(50);	//allow for some settling time due to parasitic capacitance

		ptr[i] = multisample(SIG_PIN, 3) * ( 1.0f / MAX_ADC_VALUE );
	}
	buttonSender.send();

	unsigned long usEnd = micros();
	if( usEnd - usStart < TARGET_US )
	{
		int wait = TARGET_US - (usEnd - usStart);
		delayMicroseconds( wait );
	}
}