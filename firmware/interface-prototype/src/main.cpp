#include <Arduino.h>

#include <sqid.h>
#include <sender.h>
#include <sampleFrame.h>

const uint8_t pins[] = {
	A0, 
	A1,
	A2,
	A3,
	A4,
	A5,
	A6,
	A7,
	A8,
	A9,
	A10,
	A11,
	A12
};

const int DEVICE_ID = 0;
const int SENSOR_ID = 0;

const int BUTTON_NUM = 2;
const int MAX_BUTTON_NUM = (sizeof(pins) / sizeof(pins[0]));

int buttonStates[BUTTON_NUM];

int buttonNum = 0;

using namespace sqid;

SampleFrame buttonFrame( DT_FLOAT, BUTTON_NUM );
SenderSerial buttonSender;

//test
SampleFrame resFrame( DT_FLOAT );
SenderSerial resSender;

const float ADC_RES = 12;
const float s = 1.0f / ((1 << int(ADC_RES)) - 1); // Number of steps (2^R_BITS - 1)
//----

uint16_t multisample( uint8_t pin, int samples )
{
	int sum = 0;
	for( int i = 0; i < samples; i++ )
		sum += analogRead(pin);
	return (float)sum / samples;
}

void setup()
{
	buttonNum = BUTTON_NUM > MAX_BUTTON_NUM ? MAX_BUTTON_NUM : BUTTON_NUM;

	Serial.begin(115200);

	if (!buttonSender.init(&buttonFrame, DEVICE_ID, SENSOR_ID))
		Serial.println("failed to init button sender");

	// todo: check for max pin ID
	for (int i = 0; i < buttonNum; i++)
		pinMode(pins[i], INPUT_PULLUP);

	//test
	if (!resSender.init(&resFrame, DEVICE_ID, SENSOR_ID + 1))
		Serial.println("failed to init res sender");
	pinMode(A5, INPUT);
	pinMode(12, OUTPUT);
	digitalWrite(12, HIGH);
	//----
}

void loop()
{
	// update array data
	float *ptr = reinterpret_cast<float *>(buttonFrame.getData());

	for (int i = 0; i < buttonNum; i++)
	{
		buttonStates[i] = digitalRead(pins[i]);
		ptr[i] = buttonStates[i] ? 0.0f : 1.0f;
	}
	buttonSender.send();

	//test
	ptr = reinterpret_cast<float *>(resFrame.getData());
	//*ptr = multisample(A5, 10) * s;
	int raw = analogRead(A5);
	*ptr = raw * s;
	resSender.send();
	//----

	delay(10);
}