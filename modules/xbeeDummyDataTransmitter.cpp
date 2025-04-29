#include <Arduino.h>
#include <SoftwareSerial.h>

uint8_t master_addr[] = {0x00, 0x13, 0xA2, 0x00, 0x42, 0x39, 0xE8, 0x4F};
uint8_t slave_1_addr[] = {0x00, 0x13, 0xA2, 0x00, 0x42, 0x5B, 0xE1, 0x07};
uint8_t slave_2_addr[] = {0x00, 0x13, 0xA2, 0x00, 0x42, 0x39, 0xEB, 0xCC};
uint8_t slave_3_addr[] = {0x00, 0x13, 0xA2, 0x00, 0x42, 0x39, 0xE3, 0xE2};
uint8_t broadcast_addr[] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF};


// char test_message[]= "[{'channel': 10, 'name': 'Barometer', 'value': 19.5}, {'channel': 11, 'name': 'Temperature Sensor', 'value': 19.5}, {'channel': 12, 'name': 'Barometer', 'value': 19.5}, {'channel': 13, 'name': 'Temperature Sensor', 'value': 19.5}, {'channel': 0, 'name': 'Barometer', 'value': 0.0}, {'channel': 1, 'name': 'Barometer', 'value': 0.0}, {'channel': 2, 'name': 'Barometer', 'value': 0.0}, {'channel': 0, 'name': 'Temperature Sensor', 'value': -1278.4}, {'channel': 9, 'name': 'Barometer', 'value': 122.0}]";
// char test_message[] = "{'channel': 10, 'name': 'Barometer', 'value': 3.1}";
// uint8_t test_message[] = {0x0A, 0x42, 0x61, 0x72, 0x6F, 0x6D, 0x65, 0x74, 0x65, 0x72, 0x40, 0x4C, 0xCC, 0xCD};
uint8_t slave1_message[] = {10, 115, 0, 110, 11, 103, 0, 110, 12, 115, 0, 110, 13, 103, 0, 110, 0, 115, 0, 110, 1, 115, 0, 110, 2, 115, 0, 110, 0, 103, 0, 110, 9, 115, 0, 110};
uint8_t slave2_message[] = {10, 115, 0, 120, 11, 103, 0, 120, 12, 115, 0, 120, 13, 103, 0, 120, 0, 115, 0, 120, 1, 115, 0, 120, 2, 115, 0, 120, 0, 103, 0, 120, 9, 115, 0, 120};
uint8_t slave3_message[] = {10, 115, 0, 130, 11, 103, 0, 130, 12, 115, 0, 130, 13, 103, 0, 130, 0, 115, 0, 130, 1, 115, 0, 130, 2, 115, 0, 130, 0, 103, 0, 130, 9, 115, 0, 130};
uint8_t slave4_message[] = {10, 115, 0, 140, 11, 103, 0, 140, 12, 115, 0, 140, 13, 103, 0, 140, 0, 115, 0, 140, 1, 115, 0, 140, 2, 115, 0, 140, 0, 103, 0, 140, 9, 115, 0, 140};
uint8_t test_message[] = {10, 115, 0, 195, 11, 103, 0, 195, 12, 115, 0, 195, 13, 103, 0, 195, 0, 115, 0, 0, 1, 115, 0, 0, 2, 115, 0, 0, 0, 103, 206, 16, 9, 115, 4, 196};

SoftwareSerial slave1_serial(2,3);
SoftwareSerial slave2_serial(4,5);
SoftwareSerial slave3_serial(6,7);
SoftwareSerial slave4_serial(8,9);

void send_transmit_request(SoftwareSerial serial, uint8_t dest_addr[], uint8_t message[], uint16_t message_len);
uint8_t calculateChecksum(uint8_t* frame, int length);
void receive_transmit_request();


void setup() {
  // initialize digital pin LED_BUILTIN as an output.
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(9600);
  
  slave1_serial.begin(9600);
  slave2_serial.begin(9600);
  slave3_serial.begin(9600);
  slave4_serial.begin(9600);
}

// the loop function runs over and over again forever
void loop() {

  // if (Serial.available()){
  //   Serial.println("here");
  //   Serial.write(Serial.read());
  // }

  // Serial.write(slave_message, sizeof(slave_message));
  // Serial.println("sent");
  send_transmit_request(slave1_serial, broadcast_addr, (uint8_t *)slave1_message, sizeof(slave1_message));
  send_transmit_request(slave2_serial, broadcast_addr, (uint8_t *)slave2_message, sizeof(slave2_message));
  send_transmit_request(slave3_serial, broadcast_addr, (uint8_t *)slave3_message, sizeof(slave3_message));
  send_transmit_request(slave4_serial, broadcast_addr, (uint8_t *)slave4_message, sizeof(slave4_message));
  // receive_transmit_request();
  delay(1000);

}
#define META_DATA_LEN 17
#define START_DELIMITER 0x7E

#define START_DELIMITER_OFFSET 0
void send_transmit_request(SoftwareSerial serial, uint8_t dest_addr[], uint8_t message[], uint16_t message_len){

  uint16_t format_message_len = META_DATA_LEN + message_len + 1;

  uint8_t format_message[format_message_len] = {0};
  format_message[START_DELIMITER_OFFSET] = START_DELIMITER;

  format_message[1] = (format_message_len -4) >> 8;
  format_message[2] = (format_message_len -4);

  format_message[3] = 0x10;
  format_message[4] = 0x01;

  for(int i=0; i<8; i++){
    format_message[5+i] = dest_addr[i];
  }

  format_message[13] = 0xFF;
  format_message[14] = 0xFE;

  format_message[15] = 0x00;
  format_message[16] = 0x00;

  for (uint16_t i=0; i<message_len; i++){
    format_message[META_DATA_LEN+i] = message[i];
  }

  format_message[format_message_len-1] = calculateChecksum(format_message, format_message_len);
  
  // Serial.println(format_message_len);
  // Serial.println(message_len);
  
  Serial.write(format_message, format_message_len);
  
  serial.write(format_message, format_message_len);
  // slave3_serial.write(format_message, format_message_len);

  for (uint16_t i=0; i<format_message_len; i++){
    Serial.print(format_message[i], HEX);
    Serial.print(" ");
  }
  Serial.println();
}

uint8_t calculateChecksum(uint8_t* frame, int length) {
  uint8_t sum = 0;
  for (int i = 3; i < length - 1; i++) {  // Start from Frame Type (skip 0x7E, length)
    sum += frame[i];
  }
  return 0xFF - sum;
}


void receive_transmit_request() {
  if (Serial.available() > 0) {
    if (Serial.read() == START_DELIMITER) {
      // Read length (2 bytes)
      while (Serial.available() < 2);
      uint8_t msb = Serial.read();
      uint8_t lsb = Serial.read();
      uint16_t length = (msb << 8) | lsb;

      uint8_t buffer[length+1] = {0};

      // Read the rest of the frame
      while (Serial.available() < (uint8_t)length+1);
      Serial.readBytes(buffer, length+1);

      Serial.println("received");
      Serial.write(buffer, sizeof(buffer));
      for (uint16_t i=0; i<sizeof(buffer); i++){
        Serial.print(buffer[i], HEX);
        Serial.print(" ");
      }
      Serial.println();

    }
  }
}
