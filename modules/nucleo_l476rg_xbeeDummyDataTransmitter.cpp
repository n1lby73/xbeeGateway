#include "stm32l4xx_hal.h"

#include <stdio.h>

#define UART1_RX_PIN                      GPIO_PIN_10
#define UART1_RX_PORT                     GPIOA
#define UART1_TX_PIN                      GPIO_PIN_9
#define UART1_TX_PORT                     GPIOA
#define UART1_PORT                        GPIOA

#define UART_PORT                         GPIOA


void init_GPIO_pins(void);
void init_UART(void);

uint8_t calculateChecksum(uint8_t* frame, int length);
void send_transmit_request(UART_HandleTypeDef *uart, uint8_t dest_addr[], uint8_t message[], uint16_t message_len);

uint8_t broadcast_addr[] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF};

uint8_t slave1_message[] = {10, 115, 0, 110, 11, 103, 0, 110, 12, 115, 0, 110, 13, 103, 0, 110, 0, 115, 0, 110, 1, 115, 0, 110, 2, 115, 0, 110, 0, 103, 0, 110, 9, 115, 0, 110};

UART_HandleTypeDef huart1;


int main(void) {
    HAL_Init();

    init_GPIO_pins();
    init_UART();

    while (1) {
        send_transmit_request(&huart1, broadcast_addr, (uint8_t *)slave1_message, sizeof(slave1_message));
        HAL_Delay(1000);

    }
}

extern "C" void SysTick_Handler(void) {
    HAL_IncTick();
}

void init_GPIO_pins(void) {
    __HAL_RCC_GPIOA_CLK_ENABLE();

    GPIO_InitTypeDef GPIO_InitStruct;

    GPIO_InitStruct.Pin     = UART1_RX_PIN | UART1_TX_PIN;
    GPIO_InitStruct.Mode    = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull    = GPIO_NOPULL;
    GPIO_InitStruct.Speed   = GPIO_SPEED_LOW;
    GPIO_InitStruct.Alternate = GPIO_AF7_USART2;
    HAL_GPIO_Init(UART_PORT, &GPIO_InitStruct);
}


void init_UART(void) {
    __HAL_RCC_USART1_CLK_ENABLE();

    huart1.Instance = USART1;
    huart1.Init.BaudRate = 9600;
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart1.Init.OverSampling = UART_OVERSAMPLING_16;
    HAL_UART_Init(&huart1);
}



#define META_DATA_LEN 17
#define START_DELIMITER 0x7E

#define START_DELIMITER_OFFSET 0
void send_transmit_request(UART_HandleTypeDef *uart, uint8_t dest_addr[], uint8_t message[], uint16_t message_len) {

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
  
  HAL_UART_Transmit(uart, format_message, format_message_len, HAL_MAX_DELAY);
}

uint8_t calculateChecksum(uint8_t* frame, int length) {
  uint8_t sum = 0;
  for (int i = 3; i < length - 1; i++) {  // Start from Frame Type (skip 0x7E, length)
    sum += frame[i];
  }
  return 0xFF - sum;
}


// void receive_transmit_request() {
//   if (Serial.available() > 0) {
//     if (Serial.read() == START_DELIMITER) {
//       // Read length (2 bytes)
//       while (Serial.available() < 2);
//       uint8_t msb = Serial.read();
//       uint8_t lsb = Serial.read();
//       uint16_t length = (msb << 8) | lsb;

//       uint8_t buffer[length+1] = {0};

//       // Read the rest of the frame
//       while (Serial.available() < (uint8_t)length+1);
//       Serial.readBytes(buffer, length+1);

//       Serial.println("received");
//       Serial.write(buffer, sizeof(buffer));
//       for (uint16_t i=0; i<sizeof(buffer); i++){
//         Serial.print(buffer[i], HEX);
//         Serial.print(" ");
//       }
//       Serial.println();

//     }
//   }
// }
