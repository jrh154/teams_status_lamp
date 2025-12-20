#include <FastLED.h>
#include <EEPROM.h>

// --- Configuration ---
#define NUM_LEDS 2
#define DATA_PIN A2
#define BAUD_RATE 9600

// --- CONSTANTS ---
#define DEVICE_ID "TEAMS_LAMP"
#define CONNECT_CMD "R"
#define STATUS_ON_CMD "S:ON"
#define STATUS_OFF_CMD "S:OFF"
#define CONFIG_COLOR_CMD "C:"

#define TIMEOUT_MS 10000        // 10 seconds without data -> Disconnect
#define BROADCAST_INTERVAL 1000 // 1 second
#define BLINK_INTERVAL 1000     // 1 second (500ms on, 500ms off)

// --- EEPROM ADDRESSES ---
#define ADDR_MAGIC 0
#define ADDR_ON_CALL 1  // 3 bytes (R, G, B)
#define ADDR_OFF_CALL 4 // 3 bytes (R, G, B)
#define MAGIC_BYTE 0x42

// --- Colors ---
// Default colors if EEPROM is not initialized
#define DEFAULT_COLOR_ON_CALL CRGB::Red
#define DEFAULT_COLOR_OFF_CALL CRGB::Green
#define COLOR_DISCONNECTED CRGB::Purple

// --- GLOBALS ---
CRGB leds[NUM_LEDS];
CRGB colorOnCall;
CRGB colorOffCall;

enum State {
  DISCONNECTED,
  OFF_CALL,
  ON_CALL
};

State currentState = DISCONNECTED;
unsigned long lastSerialTime = 0;
unsigned long lastBroadcastTime = 0;
String inputString = "";
bool stringComplete = false;

// --- FUNCTIONS ---

void saveColorToEEPROM(int address, CRGB color) {
  EEPROM.put(address, color);
}

void loadColors() {
  byte magic;
  EEPROM.get(ADDR_MAGIC, magic);

  if (magic == MAGIC_BYTE) {
    // Valid data exists, load it
    EEPROM.get(ADDR_ON_CALL, colorOnCall);
    EEPROM.get(ADDR_OFF_CALL, colorOffCall);
  } else {
    // Initialize EEPROM with defaults
    colorOnCall = DEFAULT_COLOR_ON_CALL;
    colorOffCall = DEFAULT_COLOR_OFF_CALL;

    EEPROM.put(ADDR_ON_CALL, colorOnCall);
    EEPROM.put(ADDR_OFF_CALL, colorOffCall);
    EEPROM.put(ADDR_MAGIC, (byte)MAGIC_BYTE);
  }
}

void updateLeds() {
  unsigned long currentMillis = millis();

  switch (currentState) {
    case DISCONNECTED:
      // Blink Purple
      if ((currentMillis / (BLINK_INTERVAL / 2)) % 2 == 0) {
        fill_solid(leds, NUM_LEDS, COLOR_DISCONNECTED);
      } else {
        fill_solid(leds, NUM_LEDS, CRGB::Black);
      }
      break;

    case OFF_CALL:
      fill_solid(leds, NUM_LEDS, colorOffCall);
      break;

    case ON_CALL:
      fill_solid(leds, NUM_LEDS, colorOnCall);
      break;
  }
  FastLED.show();
}

void handleStateLogic() {
  unsigned long currentMillis = millis();

  // 1. Timeout Check
  if (currentState != DISCONNECTED && (currentMillis - lastSerialTime > TIMEOUT_MS)) {
    currentState = DISCONNECTED;
  }

  // 2. State-Specific Logic
  switch (currentState) {
    case DISCONNECTED:
      // Broadcast ID constantly
      if (currentMillis - lastBroadcastTime >= BROADCAST_INTERVAL) {
        Serial.println(DEVICE_ID);
        lastBroadcastTime = currentMillis;
      }
      break;

    case OFF_CALL:
    case ON_CALL:
      // Passive states, waiting for Serial commands
      break;
  }
}

void handleColorConfig(String cmd) {
  // Parsing "C:ON:0xFF00FF" or "C:OFF:FF0000"
  
  int firstColon = cmd.indexOf(':');
  int secondColon = cmd.indexOf(':', firstColon + 1);

  if (firstColon == -1 || secondColon == -1) return;

  String target = cmd.substring(firstColon + 1, secondColon);
  String hexValue = cmd.substring(secondColon + 1);

  // Clean hex string
  if (hexValue.startsWith("0x") || hexValue.startsWith("0X")) {
    hexValue = hexValue.substring(2);
  }
  
  if (hexValue.length() != 6) return; 

  long number = strtol(hexValue.c_str(), NULL, 16);
  CRGB newColor = CRGB(number);

  if (target == "ON") {
    colorOnCall = newColor;
    saveColorToEEPROM(ADDR_ON_CALL, colorOnCall);
    blinkConfirmation(colorOnCall);
  } else if (target == "OFF") {
    colorOffCall = newColor;
    saveColorToEEPROM(ADDR_OFF_CALL, colorOffCall);
    blinkConfirmation(colorOffCall);
  }
}

void blinkConfirmation(CRGB color) {
  for(int i=0; i<3; i++) {
    fill_solid(leds, NUM_LEDS, CRGB::Black);
    FastLED.show();
    delay(500);
    fill_solid(leds, NUM_LEDS, color);
    FastLED.show();
    delay(500);
  }
}

void processCommand(String cmd) {
  cmd.trim();
  
  if (cmd.length() == 0) return;

  // Update heartbeat/timeout timer on any valid command
  lastSerialTime = millis();

  if (cmd.startsWith(CONFIG_COLOR_CMD)) {
    handleColorConfig(cmd);
    return;
  }

  if (currentState == DISCONNECTED) {
    if (cmd == CONNECT_CMD) {
      currentState = OFF_CALL; // Default to off-call on connect
    }
  } else {
    // We are connected (OFF_CALL or ON_CALL)
    if (cmd == STATUS_ON_CMD) {
      currentState = ON_CALL;
    } else if (cmd == STATUS_OFF_CMD) {
      currentState = OFF_CALL;
    } else if (cmd == CONNECT_CMD) {
       currentState = OFF_CALL;
    }
  }
}

void setup() {
  Serial.begin(BAUD_RATE);
  FastLED.addLeds<WS2812, DATA_PIN, GRB>(leds, NUM_LEDS);
  
  loadColors(); // Load colors from EEPROM
  
  fill_solid(leds, NUM_LEDS, CRGB::Black);
  FastLED.show();
  
  // Initialize timers
  lastSerialTime = millis();
}

void loop() {
  // 1. Read Serial
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      stringComplete = true;
    } else {
      inputString += inChar;
    }
  }

  // 2. Process Input
  if (stringComplete) {
    processCommand(inputString);
    inputString = "";
    stringComplete = false;
  }

  // 3. State Machine & Hardware Updates
  handleStateLogic();
  updateLeds();
}
