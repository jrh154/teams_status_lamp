#include <FastLED.h>

// --- Configuration ---
#define NUM_LEDS 2
#define DATA_PIN A2
#define ERROR_COLOR CRGB::Red

// --- Coms Codes ---
#define ID "TEAMS_LAMP"
#define PC_MESSAGE "R"
#define MCU_MESSAGE "S"

// --- Serial Setup ---
#define BAUD 9600

// --- Timeouts & Intervals ---
#define HEARTBEAT_TIMEOUT 10000000
#define HEARTBEAT_PULSE 1000
#define BLINK_PERIOD_SHORT 200
#define BLINK_PERIOD_LONG 300
#define BLINK_COUNT_ACK 3
#define BLINK_COUNT_ERROR 5
#define BLINK_COUNT_UNKNOWN 3

CRGB leds[NUM_LEDS];

// --- Variables ---
String incomingData = "";
bool stringComplete = false;

// Heartbeat variables
unsigned long previousTimeoutMillis = 0;
unsigned long currentTimeoutMillis = 0;
unsigned long previousHeartBeatTimer = 0;
unsigned long currentHeartBeatTimer = 0;

// LED color variables
CRGB onCallColor = CRGB::Red;
CRGB offCallColor = CRGB::Green;

// --- Helper Functions ---

// Function for blinking leds a given color, with given interval (blink period) and given number
void blinkLeds(CRGB color, int blinkPeriod, int blinks) {
  for (int i = 0; i < blinks; i++) {
    fill_solid(leds, NUM_LEDS, color);
    FastLED.show();
    delay(blinkPeriod);

    fill_solid(leds, NUM_LEDS, CRGB::Black);
    FastLED.show();
    delay(blinkPeriod);
  }
}

// Function for turning on all LEDs with single color
void turnOnLeds(CRGB color) {
  fill_solid(leds, NUM_LEDS, color);
  FastLED.show();
}

// Function for turning off all leds
void turnOffLeds() {
  fill_solid(leds, NUM_LEDS, CRGB::Black);
  FastLED.show();
}

CRGB stringNameToCRGB(String colorName) {
  // --- Primary Colors ---
  if (colorName == "BLACK") return CRGB::Black;
  if (colorName == "WHITE") return CRGB::White;
  if (colorName == "GRAY" || colorName == "GREY") return CRGB::Gray;
  if (colorName == "RED") return CRGB::Red;
  if (colorName == "GREEN") return CRGB::Green;
  if (colorName == "BLUE") return CRGB::Blue;

  // --- Secondary Colors & Warm Hues ---
  if (colorName == "YELLOW") return CRGB::Yellow;
  if (colorName == "ORANGE") return CRGB::Orange;
  if (colorName == "GOLD") return CRGB::Gold;
  if (colorName == "BROWN") return CRGB::Brown;
  if (colorName == "SALMON") return CRGB::Salmon;

  // --- Cool Hues (Cyans and Greens) ---
  if (colorName == "CYAN" || colorName == "AQUA") return CRGB::Aqua;
  if (colorName == "TEAL") return CRGB::Teal;
  if (colorName == "LIME") return CRGB::Lime;
  if (colorName == "FORESTGREEN") return CRGB::ForestGreen;
  if (colorName == "SEAGREEN") return CRGB::SeaGreen;
  if (colorName == "DEEPSKYBLUE") return CRGB::DeepSkyBlue;

  // --- Purples and Pinks ---
  if (colorName == "MAGENTA" || colorName == "FUCHSIA") return CRGB::Magenta;
  if (colorName == "PURPLE") return CRGB::Purple;
  if (colorName == "VIOLET") return CRGB::Violet;
  if (colorName == "PINK") return CRGB::Pink;
  if (colorName == "HOTPINK") return CRGB::HotPink;
  if (colorName == "INDIGO") return CRGB::Indigo;

  // Unknown color
  blinkLeds(CRGB::Violet, BLINK_PERIOD_SHORT, BLINK_COUNT_UNKNOWN);
  return CRGB::Black; // Default return to avoid warnings
}

// --- USB ID Functions ---

// Broadcast an ID while not connected to the pc-side script
void broadcastID() {
  while(true) {
    Serial.println(ID); // broadcast on Serial for script to listen to
    Serial.flush();
    
    // if Serial is empty, do nothing, if it does have something, check for connection request from PC
    if (Serial.available() != 0) {
      // Read any message on serial and trim any white space as needed
      String message = Serial.readString();
      message.trim();

      // If connection request from PC as expected, proceed to main script
      if(message == PC_MESSAGE) {
        blinkLeds(CRGB::Green, BLINK_PERIOD_LONG, BLINK_COUNT_ACK); // Blink to acknowledge connection
        turnOnLeds(offCallColor);
        
        // Reset timers as needed
        previousTimeoutMillis = millis();
        previousHeartBeatTimer = millis();
        
        return; // Exit the function
      }
    }
    delay(500);
  }
}

// --- Teams Lamp Functions ---

// Read in color command and set colors accordingly
void changeColor(String command) {
  // Expected Command Structure
  // SET_COLOR:STATUS_TYPE:VALUE_TYPE:VALUE
  // STATUS_TYPE=ON_CALL,OFF_CALL
  // VALUE_TYPE=HEX (0xFFFFFF), RGB (R,G,B), NAME (defined by FastLED)
  // VALUE=Color Value 

  // Find colon indexes
  int firstColon = command.indexOf(":");
  int secondColon = command.indexOf(":", firstColon + 1);
  int thirdColon = command.indexOf(":", secondColon + 1);

  if (firstColon == -1 || secondColon == -1 || thirdColon == -1) {
    blinkLeds(CRGB::Violet, BLINK_PERIOD_SHORT, BLINK_COUNT_UNKNOWN);
    return;
  }

  // Split command string
  String status = command.substring(firstColon + 1, secondColon);
  String valueType = command.substring(secondColon + 1, thirdColon);
  String value = command.substring(thirdColon + 1);
  CRGB color = CRGB::Black;

  // Different conversion method based on type passed
  if (valueType == "HEX") {
    const char* hexCstr = value.c_str(); 
    unsigned long hexValue = strtol(hexCstr, NULL, 16); 
    color = hexValue;

  } else if (valueType == "RGB") {
    // Parse R,G,B string
    int comma1 = value.indexOf(',');
    int comma2 = value.indexOf(',', comma1 + 1);
    
    if (comma1 != -1 && comma2 != -1) {
      int r = value.substring(0, comma1).toInt();
      int g = value.substring(comma1 + 1, comma2).toInt();
      int b = value.substring(comma2 + 1).toInt();
      color = CRGB(r, g, b);
    } else {
        blinkLeds(CRGB::Violet, BLINK_PERIOD_SHORT, BLINK_COUNT_UNKNOWN);
    }

  } else if (valueType == "NAME") {
    color = stringNameToCRGB(value);
  }
  
  // Change color based on status
  if (status == "ON_CALL") {
    onCallColor = color;
  } else if (status == "OFF_CALL") {
    offCallColor = color;
  } else {
    blinkLeds(CRGB::Violet, BLINK_PERIOD_SHORT, BLINK_COUNT_UNKNOWN);
  }
}

void setStatus(String command) {
  // Command structure:
  // SET_STATUS:STATUS
  // STATUS=ON_CALL,OFF_CALL

  int firstColon = command.indexOf(":");
  String status = command.substring(firstColon + 1);

  // Perform action based on status
  if (status.equals("ON_CALL")) {
    turnOnLeds(onCallColor);
  } else if (status.equals("OFF_CALL")) {
    turnOnLeds(offCallColor);
  } 
}

void parseCommand(String command) {
  if (command.startsWith("SET_COLOR")) {
    changeColor(command);
  } else if(command.startsWith("SET_STATUS")) {
    setStatus(command);
  }
}

// --- Setup and Loop ---

void setup() {
  FastLED.addLeds<WS2812, DATA_PIN, GRB>(leds, NUM_LEDS); 
  Serial.begin(BAUD); 
  broadcastID();
}

void loop() {
  // Read timers for heartbeat
  currentTimeoutMillis = millis(); 
  currentHeartBeatTimer = millis(); 
  
  // Read the entire Serial before parsing
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    incomingData += inChar;
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
  
  // After string fully received interpret the command
  if (stringComplete) {
    incomingData.trim(); 
    
    // Check if heartbeat signal directly here
    if (incomingData.equals(PC_MESSAGE)) {
      previousTimeoutMillis = millis(); 
    } else {
      parseCommand(incomingData);
    }
    
    incomingData = "";
    stringComplete = false;
  }

  // Pulse a heartbeat 
  if (currentHeartBeatTimer - previousHeartBeatTimer >= HEARTBEAT_PULSE) {
    Serial.println(MCU_MESSAGE); 
    Serial.flush();
    previousHeartBeatTimer = millis();
    if (currentTimeoutMillis - previousTimeoutMillis > HEARTBEAT_TIMEOUT) {
       blinkLeds(CRGB::Violet, BLINK_PERIOD_SHORT, BLINK_COUNT_ERROR);
       broadcastID();
    }
  }
}
