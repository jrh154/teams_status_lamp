#include <FastLED.h>

////
////
//// Variable Setup
////
////

// LED Setup
#define NUM_LEDS 2
#define DATA_PIN A1
#define ERROR_COLOR CRGB::Red
CRGB leds[NUM_LEDS];


// COMS Codes
#define ID "TEAMS_LAMP"
#define PC_MESSAGE "R"
#define MCU_MESSAGE "S"

// Serial Setup
#define BAUD 115200

// Heartbeat Timeout
#define HEARTBEAT_TIMEOUT 10000
#define HEARTBEAT_PULSE 1000

// Variable Initialization
String incoming_data = "";
bool stringComplete = false;

// hearbeat variables
unsigned long previousTimeoutMillis = 0;
unsigned long currentTimeoutMillis = 0;
unsigned long previousHeartBeatTimer = 0;
unsigned long currentHeartBeatTimer = 0;

// led color variables
CRGB on_call_color = CRGB::Red;
CRGB off_call_color = CRGB::Green;

//////////////////////
/////
///// HELPER FUNCTIONS
/////
//////////////////////


//////////////
/// LED Functions
//////////////

// Function for blinking leds a given color, with given interval (blink period) and given number 
void blinkLeds(CRGB color, int blink_period, int blinks) {
  for (int i = 1; i <= blinks; i++) {
    fill_solid(leds, NUM_LEDS, color);
    FastLED.show();
    delay(blink_period);

    fill_solid(leds, NUM_LEDS, CRGB::Black);
    FastLED.show();
    delay(blink_period);
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
  if (colorName == "BLACK") {
    return CRGB::Black;
  } else if (colorName == "WHITE") {
    return CRGB::White;
  } else if (colorName == "GRAY" || colorName == "GREY") {
    return CRGB::Gray;
  } else if (colorName == "RED") {
    return CRGB::Red;
  } else if (colorName == "GREEN") {
    return CRGB::Green;
  } else if (colorName == "BLUE") {
    return CRGB::Blue;
  } 

  // --- Secondary Colors & Warm Hues ---
  else if (colorName == "YELLOW") {
    return CRGB::Yellow;
  } else if (colorName == "ORANGE") {
    return CRGB::Orange;
  } else if (colorName == "GOLD") {
    return CRGB::Gold;
  } else if (colorName == "BROWN") {
    return CRGB::Brown;
  } else if (colorName == "SALMON") {
    return CRGB::Salmon;
  } 

  // --- Cool Hues (Cyans and Greens) ---
  else if (colorName == "CYAN" || colorName == "AQUA") {
    return CRGB::Aqua;
  } else if (colorName == "TEAL") {
    return CRGB::Teal;
  } else if (colorName == "LIME") {
    return CRGB::Lime;
  } else if (colorName == "FORESTGREEN") {
    return CRGB::ForestGreen;
  } else if (colorName == "SEAGREEN") {
    return CRGB::SeaGreen;
  } else if (colorName == "DEEPSKYBLUE") {
    return CRGB::DeepSkyBlue;
  } 

  // --- Purples and Pinks ---
  else if (colorName == "MAGENTA" || colorName == "FUCHSIA") {
    return CRGB::Magenta;
  } else if (colorName == "PURPLE") {
    return CRGB::Purple;
  } else if (colorName == "VIOLET") {
    return CRGB::Violet;
  } else if (colorName == "PINK") {
    return CRGB::Pink;
  } else if (colorName == "HOTPINK") {
    return CRGB::HotPink;
  } else if (colorName == "INDIGO") {
    return CRGB::Indigo;
  }

  else {
    // Serial.println("Color Not Recognized");
    blinkLeds(CRGB::Violet, 200, 3);
  }
}

//////////////
///USB ID Functions
//////////////

// Broadcast an ID while not connected to the pc-side script
void broadcastID() {
  while(true) {

    Serial.println(ID); // broadcast on Serial for script to listen to
    
    //if Serial is empty, do nothing, if it doe shave something, check for connection request from PC
    if (Serial.available() != 0) {
      // Read any messag on serial and trim any white space as needed
      String message = Serial.readString();
      message.trim();

      // Debugging prints, not needed
      //Serial.print("Received Connection Request: ");
      //Serial.println(message);

      // If connection request from PC as expected, proceed to main script
      if(message == PC_MESSAGE) {
        //Serial.println("Connection Received"); // Debugging
        //Serial.println(MCU_MESSAGE); // Debugging
        blinkLeds(CRGB::Green, 300, 3); // Blink to acknowledge connection
        turnOnLeds(off_call_color);
        
        // Reset timers as needed
        previousTimeoutMillis = millis();
        previousHeartBeatTimer = millis();
        
        return; // Exit the function
      }
    }
    delay(100);
  }
}

// void heartbeatThread(String incoming_data) {
//   Serial.println(MCU_MESSAGE); // send initial heartbeat
//   Serial.flush();

//   // Debug printing
//   // Serial.print("Time since last PC heartbeat received");
//   // Serial.println(currentTimeoutMillis - previousTimeoutMillis);\
//   // Serial.print("Incoming data was: ");
//   // Serial.println(incoming_data);
//   // Serial.flush();

//   if (incoming_data==PC_MESSAGE) {
//     // Serial.println("PC Heartbeat Received");
//     // Serial.flush();
//     previousTimeoutMillis = millis();
//     return;
//   }

//   if (currentTimeoutMillis - previousTimeoutMillis > HEARTBEAT_TIMEOUT) {
//     //Serial.println("ERROR! LOST CONNECTION WITH PC...RESTARTING BROADCAST");
//     blinkLeds(CRGB::Violet, 200, 5);
//     broadcastID();
//   }
// }

//////////////
/// Teams Lamp Functions
//////////////

// Read in color command and set colors accordingly
void changeColor(String command) {
  // Expected Command Structure
  // SET_COLOR:STATUS_TYPE:VALUE_TYPE:VALUE
  // STATUS_TYPE=ON_CALL,OFF_CALL (could extend to more for future)
  // VALUE_TYPE=HEX (0xFFFFFF), RGB (R,G,B), COLOR (defined by FastLED)
  // VALUE=Color Value 

  // Find colon indexes
  int first_colon = command.indexOf(":");
  int second_colon = command.indexOf(":", first_colon+1);
  int third_colon = command.indexOf(":", second_colon+1);

  // Split command string
  String status = command.substring(first_colon+1, second_colon);
  String value_type = command.substring(second_colon+1, third_colon);
  String value = command.substring(third_colon+1);
  CRGB color = CRGB::Black;

  // Different conversion method based on type passed
  if (value_type == "HEX") {
    //Serial.print("Value Type is HEX...setting color to: ");
    //Serial.println(value);
    
    // Convert string to hex
    const char* hexCstr = value.c_str(); // get a pointer to the character array for string (required for strtol)
    unsigned long hexValue = strtol(hexCstr, NULL, 16); // convert value string to hex

    // Set the color
    color = hexValue;

  } else if (value_type == "RGB") {
    //Serial.print("Value Type is RGB...setting color to: ");
    //Serial.println("value");

    // TO BE IMPLEMENTED!

  } else if (value_type == "NAME") {
    //Serial.print("Value Type is NAME...setting color to: ");
    //Serial.println(value);
    
    color = stringNameToCRGB(value);
  }
  
  // Change color based on 
  if(status == "ON_CALL") {
    on_call_color = color;
  } else if(status == "OFF_CALL") {
    off_call_color = color;
  } else {
    //Consider wrong status value provided
    //Serial.print("Status type not recognized...read: ");
    //Serial.println(status);
    blinkLeds(CRGB::Violet, 200, 3);
    }

}

void setStatus(String command) {
  //Command structure:
  //SET_STATUS:STATUS
  //STATUS=ON_CALL,OFF_CALL

  int first_colon = command.indexOf(":");
  String status = command.substring(first_colon+1);

  // Perform action based on status...can extend this as needed
  if(status == "ON_CALL") {
    //Serial.println("Changing LED status to: ON CALL");
    turnOnLeds(on_call_color);
  } else if(status == "OFF_CALL") {
    //Serial.println("Changing LED status to OFF_CALL");
    turnOnLeds(off_call_color);
  } else {
    //Serial.println("Status type unrecognized");
  }

}

void parseCommand(String command) {

  // debugging
  //Serial.print("Command Received: ");
  //Serial.println(command);

  // Send to appropriate function based on command...can expand this here
  if (command.startsWith("SET_COLOR")) {
    //Serial.println("Got command to set color");
    changeColor(command);
  } else if(command.startsWith("SET_STATUS")) {
    //Serial.println("Got commmand to change status");
    setStatus(command);
  } else {
    //Serial.println("Command not recognized!");
  }
}
/////////////////////
////
//// Setup and Loop
////
/////////////////////

void setup() {
  FastLED.addLeds<WS2812, DATA_PIN, GRB>(leds, NUM_LEDS); // Initialize LED strip
  Serial.begin(BAUD); // Set up Serial
  broadcastID();
}

void loop() {
  //Read timers for heart beat
  currentTimeoutMillis = millis(); // Track how long since last received heartbeat from PC
  currentHeartBeatTimer = millis(); // Track how long since sending last heartbeat message
  
  // Read the entire Serial before parsing
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    incoming_data += inChar;
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
  
  // After string fully received interpret the command
  if (stringComplete) {
    incoming_data.trim() // Trim the whitespace
    
    // Check if hearbeat signal directly here and reset accordingly, otherwise parse the command
    if (incoming_data.equals(PC_MESSAGE)) {
      previousTimeoutMillis = millis(); //reset the heartbeat timer
    } else {
      parseCommand(input_string);
    }
    // Reset the string reader
    input_string = "";
    stringComplte = false;
  }

  // Pulse a heartbeat once per heartbeat pulse...may want to play around with timing here
  if (currentHeartBeatTimer - previousHeartBeatTimer >=HEARTBEAT_PULSE) {
    Serial.println(MCU_MESSAGE); // send heartbeat to PC
    Serial.flush();
  
    if (currentTimeoutMillis - previousTimeoutMillis > HEARTBEAT_TIMEOUT) {
       //Serial.println("ERROR! LOST CONNECTION WITH PC...RESTARTING BROADCAST");
       blinkLeds(CRGB::Violet, 200, 5);
       broadcastID();
    }
  }
}


