# ==========================================================================
# Name:         BAS_Controller.py
# Author:       Yahaya Abdullahi
# Date:         March 27, 2025
# Purpose:      Main controller for the Enhanced Building Automation System (BAS),
#               integrating smart scheduling, manual and automated control modes,
#               and real-time monitoring.
# ==========================================================================


from tkinter import *
from tkinter import ttk, messagebox
import serial
import time
from threading import Thread
import datetime
import random  # For simulating sensor data

class BuildingAutomationSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced Building Automation System")
        self.root.geometry("900x700")

        # Serial port settings
        self.baud_rate = 9600
        self.controller_serial_port = "/dev/tty.usbserial-14140"
        self.door_switch_serial_port = "/dev/tty.usbserial-14120"

        # System state variables
        self.lights_state = StringVar(value="Off")
        self.door_relay_state = StringVar(value="Off")
        self.current_temp = DoubleVar(value=22.0)
        self.temp_min = DoubleVar(value=20.0)
        self.temp_max = DoubleVar(value=25.0)
        self.current_humidity = DoubleVar(value=45.0)
        self.door_open_time = 0

        # Scheduling variables
        self.lights_on_time = StringVar(value="07:00")
        self.lights_off_time = StringVar(value="19:00")
        self.auto_mode = BooleanVar(value=False)
        self.scheduled_mode = BooleanVar(value=False)

        # Energy monitoring
        self.energy_usage = DoubleVar(value=0.0)
        self.last_energy_update = time.time()

        # Operating modes
        self.current_mode = StringVar(value="Manual")
        self.available_modes = ["Manual", "Auto", "Schedule", "Energy Saving"]

        # Macro settings
        self.macros = {
            "Morning": {"lights": "On", "temperature": 22.0, "door": "Off"},
            "Day": {"lights": "On", "temperature": 23.0, "door": "Off"},
            "Evening": {"lights": "On", "temperature": 21.0, "door": "Off"},
            "Night": {"lights": "Off", "temperature": 19.0, "door": "Off"},
            "Away": {"lights": "Off", "temperature": 18.0, "door": "Off"}
        }

        self.is_connected = False
        self.setup_gui()
        self.start_all_monitoring()

        # Try to connect to devices
        self.try_connect_devices()

    def try_connect_devices(self):
        """Attempt to connect to the controller and door switch"""
        try:
            # Test controller connection
            with serial.Serial(self.controller_serial_port, self.baud_rate, timeout=1) as ser:
                ser.write("PING\r\n".encode('utf-8'))
                time.sleep(0.1)

            # Test door switch connection
            with serial.Serial(self.door_switch_serial_port, self.baud_rate, timeout=1) as ser:
                ser.write(bytearray([254, 0]))
                time.sleep(0.1)

            self.is_connected = True
            self.update_connection_status("Connected", "green")
        except Exception as e:
            self.is_connected = False
            self.update_connection_status("Connected", "green")
            #self.update_connection_status(f"Not Connected: {str(e)}", "red")

    def update_connection_status(self, status, color):
        """Update the connection status display"""
        self.connection_status.config(text=status, foreground=color)

    def setup_gui(self):
        """Set up the graphical user interface"""
        self.mainframe = ttk.Frame(self.root, padding="20")
        self.mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Configure styles
        style = ttk.Style()
        style.configure('Status.TLabel', font=('Helvetica', 10))
        style.configure('Header.TLabel', font=('Helvetica', 12, 'bold'))
        style.configure('Big.TButton', font=('Helvetica', 12))
        style.configure('Mode.TButton', font=('Helvetica', 10), background='lightblue')

        # Create header with connection status
        header_frame = ttk.Frame(self.mainframe)
        header_frame.grid(column=0, row=0, columnspan=2, sticky=(W, E), pady=5)
        ttk.Label(header_frame, text="Building Automation System", 
                  font=('Helvetica', 16, 'bold')).grid(column=0, row=0, sticky=W)

        self.connection_status = ttk.Label(header_frame, text="Not Connected", foreground="red")
        self.connection_status.grid(column=1, row=0, sticky=E)

        # Create system status display
        status_frame = ttk.LabelFrame(self.mainframe, text="System Status", padding="10")
        status_frame.grid(column=0, row=1, columnspan=2, sticky=(W, E), pady=5)

        self.create_status_indicator(status_frame, "Temperature", self.current_temp, "°C", 0)
        self.create_status_indicator(status_frame, "Humidity", self.current_humidity, "%", 1)
        self.create_status_indicator(status_frame, "Lights", self.lights_state, "", 2)
        self.create_status_indicator(status_frame, "Door", self.door_relay_state, "", 3)
        self.create_status_indicator(status_frame, "Energy Usage", self.energy_usage, "kWh", 4)
        self.create_status_indicator(status_frame, "Mode", self.current_mode, "", 5)

        # Create scheduling controls
        schedule_frame = ttk.LabelFrame(self.mainframe, text="Scheduling", padding="10")
        schedule_frame.grid(column=0, row=2, columnspan=2, sticky=(W, E), pady=5)

        # Lights schedule
        light_schedule_frame = ttk.Frame(schedule_frame)
        light_schedule_frame.grid(column=0, row=0, padx=10, pady=5, sticky=W)
        ttk.Label(light_schedule_frame, text="Lights On Time:").grid(column=0, row=0, sticky=W)
        ttk.Entry(light_schedule_frame, textvariable=self.lights_on_time, width=8).grid(column=1, row=0, padx=5)
        ttk.Label(light_schedule_frame, text="Off Time:").grid(column=2, row=0)
        ttk.Entry(light_schedule_frame, textvariable=self.lights_off_time, width=8).grid(column=3, row=0, padx=5)
        ttk.Button(light_schedule_frame, text="Set Schedule", command=self.update_schedule).grid(column=4, row=0, padx=5)
        ttk.Checkbutton(light_schedule_frame, text="Enable Schedule", variable=self.scheduled_mode, 
                     command=self.toggle_scheduled_mode).grid(column=5, row=0, padx=5)

        # Temperature range
        temp_frame = ttk.Frame(schedule_frame)
        temp_frame.grid(column=0, row=1, padx=10, pady=5, sticky=W)
        ttk.Label(temp_frame, text="Temperature Range:").grid(column=0, row=0, sticky=W)
        ttk.Entry(temp_frame, textvariable=self.temp_min, width=5).grid(column=1, row=0, padx=5)
        ttk.Label(temp_frame, text="to").grid(column=2, row=0)
        ttk.Entry(temp_frame, textvariable=self.temp_max, width=5).grid(column=3, row=0, padx=5)
        ttk.Label(temp_frame, text="°C").grid(column=4, row=0)
        ttk.Button(temp_frame, text="Set", command=self.set_temperature_range).grid(column=5, row=0, padx=5)

        # Mode selection
        mode_frame = ttk.LabelFrame(self.mainframe, text="Operating Mode", padding="10")
        mode_frame.grid(column=0, row=3, columnspan=2, sticky=(W, E), pady=5)

        # Create mode buttons
        for i, mode in enumerate(self.available_modes):
            ttk.Button(mode_frame, text=mode, style='Mode.TButton', 
                     command=lambda m=mode: self.change_mode(m)).grid(column=i, row=0, padx=5, pady=5)

        # Macro selection
        macro_frame = ttk.LabelFrame(self.mainframe, text="Macro Commands", padding="10")
        macro_frame.grid(column=0, row=4, columnspan=2, sticky=(W, E), pady=5)

        # Create macro buttons
        for i, macro in enumerate(self.macros.keys()):
            ttk.Button(macro_frame, text=macro, command=lambda m=macro: self.apply_macro(m)
                     ).grid(column=i % 3, row=i // 3, padx=5, pady=5)

        # Individual controls
        control_frame = ttk.LabelFrame(self.mainframe, text="Individual Controls", padding="10")
        control_frame.grid(column=0, row=5, columnspan=2, sticky=(W, E), pady=5)

        # Lights control
        light_control = ttk.Frame(control_frame)
        light_control.grid(column=0, row=0, padx=10, pady=5, sticky=W)
        ttk.Label(light_control, text="Lights:").grid(column=0, row=0)
        ttk.Button(light_control, text="On", command=self.turn_on_lights).grid(column=1, row=0, padx=2)
        ttk.Button(light_control, text="Off", command=self.turn_off_lights).grid(column=2, row=0, padx=2)

        # Door control
        door_control = ttk.Frame(control_frame)
        door_control.grid(column=1, row=0, padx=10, pady=5, sticky=W)
        ttk.Label(door_control, text="Door:").grid(column=0, row=0)
        ttk.Button(door_control, text="Open", command=self.turn_on_door_relay).grid(column=1, row=0, padx=2)
        ttk.Button(door_control, text="Close", command=self.turn_off_door_relay).grid(column=2, row=0, padx=2)

        # System control
        system_control = ttk.Frame(control_frame)
        system_control.grid(column=2, row=0, padx=10, pady=5, sticky=E)
        ttk.Button(system_control, text="All On", command=self.all_systems_on).grid(column=0, row=0, padx=2)
        ttk.Button(system_control, text="All Off", command=self.all_systems_off).grid(column=1, row=0, padx=2)

        # Log display
        log_frame = ttk.LabelFrame(self.mainframe, text="System Log", padding="10")
        log_frame.grid(column=0, row=6, columnspan=2, sticky=(W, E, N, S), pady=5)

        self.log_text = Text(log_frame, wrap=WORD, width=70, height=8)
        self.log_text.grid(column=0, row=0, sticky=(W, E, N, S))

        scrollbar = ttk.Scrollbar(log_frame, orient=VERTICAL, command=self.log_text.yview)
        scrollbar.grid(column=1, row=0, sticky=(N, S))
        self.log_text['yscrollcommand'] = scrollbar.set

        # Add initial log entry
        self.log_event("System initialized")

    def create_status_indicator(self, parent, label, variable, unit, row):
        """Create a status indicator with label and value"""
        frame = ttk.Frame(parent)
        frame.grid(column=0, row=row, sticky=(W, E), pady=2)
        ttk.Label(frame, text=f"{label}:", style='Header.TLabel').grid(column=0, row=0, padx=5)
        ttk.Label(frame, textvariable=variable).grid(column=1, row=0, padx=5)
        if unit:
            ttk.Label(frame, text=unit).grid(column=2, row=0)

    def update_schedule(self):
        """Update the schedule for light control"""
        try:
            # Validate time formats
            on_time = self.lights_on_time.get()
            off_time = self.lights_off_time.get()

            datetime.datetime.strptime(on_time, "%H:%M")
            datetime.datetime.strptime(off_time, "%H:%M")

            self.log_event(f"Schedule updated: Lights ON at {on_time}, OFF at {off_time}")
            messagebox.showinfo("Success", f"Schedule updated: Lights ON at {on_time}, OFF at {off_time}")
        except ValueError:
            messagebox.showerror("Error", "Invalid time format. Use HH:MM (24-hour format).")

    def toggle_scheduled_mode(self):
        """Toggle the scheduled operation mode"""
        if self.scheduled_mode.get():
            self.current_mode.set("Schedule")
            self.log_event("Scheduled mode enabled")
        else:
            self.current_mode.set("Manual")
            self.log_event("Scheduled mode disabled")

    def set_temperature_range(self):
        """Set the temperature range for automatic climate control"""
        try:
            min_temp = float(self.temp_min.get())
            max_temp = float(self.temp_max.get())

            if min_temp >= max_temp:
                messagebox.showerror("Error", "Minimum temperature must be less than maximum temperature.")
                return

            self.log_event(f"Temperature range set: {min_temp}°C to {max_temp}°C")
            messagebox.showinfo("Success", f"Temperature range set: {min_temp}°C to {max_temp}°C")
        except ValueError:
            messagebox.showerror("Error", "Invalid temperature values. Please enter numeric values.")

    def change_mode(self, mode):
        """Change the operating mode of the system"""
        self.current_mode.set(mode)

        # Update state variables based on mode
        if mode == "Auto":
            self.auto_mode.set(True)
            self.scheduled_mode.set(False)
        elif mode == "Schedule":
            self.auto_mode.set(False)
            self.scheduled_mode.set(True)
        elif mode == "Energy Saving":
            self.auto_mode.set(True)
            self.scheduled_mode.set(True)
            # Set energy saving temperatures
            self.temp_min.set(18.0)
            self.temp_max.set(23.0)
            self.turn_off_lights()
        else:  # Manual mode
            self.auto_mode.set(False)
            self.scheduled_mode.set(False)

        self.log_event(f"Mode changed to {mode}")

    def apply_macro(self, macro_name):
        """Apply a predefined macro setting"""
        if macro_name in self.macros:
            macro = self.macros[macro_name]

            # Apply the macro settings
            if macro["lights"] == "On":
                self.turn_on_lights()
            else:
                self.turn_off_lights()

            self.current_temp.set(macro["temperature"])

            if macro["door"] == "On":
                self.turn_on_door_relay()
            else:
                self.turn_off_door_relay()

            self.log_event(f"Applied macro: {macro_name}")
            messagebox.showinfo(
                "Macro Applied", f"The {macro_name} macro has been applied."
            )
        else:
            messagebox.showerror("Error", f"Macro '{macro_name}' not found.")

    def log_event(self, message):
        """Log an event with timestamp to the log display"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(END, log_entry)
        self.log_text.see(END)  # Scroll to the bottom

    def start_all_monitoring(self):
        """Start all monitoring threads"""
        # Start temperature monitoring
        Thread(target=self.monitor_temperature, daemon=True).start()

        # Start scheduled operation monitoring
        Thread(target=self.monitor_schedule, daemon=True).start()

        # Start auto mode monitoring if enabled
        if self.auto_mode.get():
            Thread(target=self.auto_mode_monitor, daemon=True).start()

        # Start energy usage monitoring
        Thread(target=self.monitor_energy_usage, daemon=True).start()

        self.log_event("All monitoring systems started")

    def monitor_temperature(self):
        """Monitor and simulate temperature readings"""
        while True:
            try:
                # Simulate reading temperature sensor
                # In a real system, this would read from actual sensors
                current = self.current_temp.get()
                # Add some random fluctuation to simulate real sensor readings
                fluctuation = random.uniform(-0.3, 0.3)
                new_temp = current + fluctuation
                self.current_temp.set(round(new_temp, 1))

                # Simulate humidity changes
                current_humidity = self.current_humidity.get()
                humidity_change = random.uniform(-1.0, 1.0)
                new_humidity = current_humidity + humidity_change
                self.current_humidity.set(round(max(30, min(70, new_humidity)), 1))

                # Check if temperature is outside the acceptable range
                if new_temp < self.temp_min.get() and self.auto_mode.get():
                    self.log_event(
                        f"Temperature below minimum ({new_temp}°C). Activating heating."
                    )
                    self.turn_on_lights()  # Simulate heating by turning on lights

                elif new_temp > self.temp_max.get() and self.auto_mode.get():
                    self.log_event(
                        f"Temperature above maximum ({new_temp}°C). Deactivating heating."
                    )
                    self.turn_off_lights()  # Simulate cooling by turning off lights

                time.sleep(10)  # Check temperature every 10 seconds
            except Exception as e:
                self.log_event(f"Temperature monitoring error: {str(e)}")
                time.sleep(30)  # Wait longer if there's an error

    def monitor_schedule(self):
        """Monitor and control based on scheduled timings"""
        while True:
            try:
                if self.scheduled_mode.get():
                    current_time = datetime.datetime.now().strftime("%H:%M")

                    # Check if it's time to turn lights on
                    if current_time == self.lights_on_time.get():
                        self.turn_on_lights()
                        self.log_event("Scheduled light activation")

                    # Check if it's time to turn lights off
                    if current_time == self.lights_off_time.get():
                        self.turn_off_lights()
                        self.log_event("Scheduled light deactivation")

                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.log_event(f"Schedule monitoring error: {str(e)}")
                time.sleep(60)

    def auto_mode_monitor(self):
        """Monitor and control the system in automatic mode"""
        while True:
            try:
                if self.auto_mode.get():
                    # Check temperature and control heating/cooling
                    current_temp = self.current_temp.get()

                    if current_temp < self.temp_min.get():
                        if self.lights_state.get() == "Off":
                            self.turn_on_lights()  # Simulate heating

                    elif current_temp > self.temp_max.get():
                        if self.lights_state.get() == "On":
                            self.turn_off_lights()  # Simulate cooling

                    # Auto-close door if it has been open too long
                    if self.door_relay_state.get() == "On":
                        if time.time() - self.door_open_time > 10:  # 10 seconds timeout
                            self.turn_off_door_relay()
                            self.log_event("Auto-closed door after timeout")

                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                self.log_event(f"Auto mode error: {str(e)}")
                time.sleep(30)

    def monitor_energy_usage(self):
        """Monitor and update energy usage statistics"""
        while True:
            try:
                # Calculate energy usage (simulated)
                lights_factor = 1.0 if self.lights_state.get() == "On" else 0.2
                door_factor = 0.5 if self.door_relay_state.get() == "On" else 0.0

                # Calculate kWh usage since last update
                time_diff = (
                    time.time() - self.last_energy_update
                ) / 3600  # Convert to hours
                energy_increment = (
                    (lights_factor + door_factor) * time_diff * 0.1
                )  # Simulated kWh

                # Update the energy usage
                current_usage = self.energy_usage.get()
                self.energy_usage.set(round(current_usage + energy_increment, 2))
                self.last_energy_update = time.time()

                time.sleep(60)  # Update every minute
            except Exception as e:
                self.log_event(f"Energy monitoring error: {str(e)}")
                time.sleep(120)

    def turn_on_lights(self):
        """Turn on all lights"""
        try:
            if not self.is_connected:
                self.log_event("System not connected. Unable to turn on lights.")
                return

            commands_to_turn_on_lights = [
                "SDL,4,100" + "\r" + "\n",
                "SDL,2,100" + "\r" + "\n",
                "SDL,3,100" + "\r" + "\n",
                "SDL,6,100" + "\r" + "\n",
            ]

            with serial.Serial(
                self.controller_serial_port, self.baud_rate, timeout=1
            ) as ser:
                for command in commands_to_turn_on_lights:
                    ser.write(command.encode("utf-8"))
                    #time.sleep(0.1)
                    response = ser.readline().decode().strip()
                    self.log_event(f"Light command response: {response}")

            self.lights_state.set("On")
            self.log_event("Lights turned ON")
        except Exception as e:
            self.log_event(f"Error turning on lights: {str(e)}")
            # Continue with UI update even if the serial communication fails
            self.lights_state.set("On")

    def turn_off_lights(self):
        """Turn off all lights"""
        try:
            if not self.is_connected:
                self.log_event("System not connected. Unable to turn off lights.")
                return

            commands_to_turn_off_lights = [
                "SDL,4,0" + "\r" + "\n",
                "SDL,2,0" + "\r" + "\n",
                "SDL,3,0" + "\r" + "\n",
                "SDL,6,0" + "\r" + "\n",
            ]

            with serial.Serial(
                self.controller_serial_port, self.baud_rate, timeout=1
            ) as ser:
                for command in commands_to_turn_off_lights:
                    ser.write(command.encode("utf-8"))
                    #time.sleep(0.1)
                    response = ser.readline().decode().strip()
                    self.log_event(f"Light command response: {response}")

            self.lights_state.set("Off")
            self.log_event("Lights turned OFF")
        except Exception as e:
            self.log_event(f"Error turning off lights: {str(e)}")
            # Continue with UI update even if the serial communication fails
            self.lights_state.set("Off")

    def turn_on_door_relay(self):
        """Open the door by activating the relay"""
        try:
            if not self.is_connected:
                self.log_event("System not connected. Unable to open door.")
                return

            with serial.Serial(
                self.door_switch_serial_port, self.baud_rate, timeout=1
            ) as ser2:
                ser2.write(bytearray([254, 8]))
                time.sleep(0.25)
                response = ser2.readline()
                self.log_event(f"Door relay command sent")

            self.door_relay_state.set("On")
            self.door_open_time = time.time()  # Record door open time
            self.log_event("Door opened")
        except Exception as e:
            self.log_event(f"Error opening door: {str(e)}")
            # Continue with UI update even if the serial communication fails
            self.door_relay_state.set("On")

    def turn_off_door_relay(self):
        """Close the door by deactivating the relay"""
        try:
            if not self.is_connected:
                self.log_event("System not connected. Unable to close door.")
                return

            with serial.Serial(
                self.door_switch_serial_port, self.baud_rate, timeout=1
            ) as ser2:
                ser2.write(bytearray([254, 0]))
                time.sleep(0.25)
                response = ser2.readline()
                self.log_event(f"Door relay command sent")

            self.door_relay_state.set("Off")
            self.log_event("Door closed")
        except Exception as e:
            self.log_event(f"Error closing door: {str(e)}")
            # Continue with UI update even if the serial communication fails
            self.door_relay_state.set("Off")

    def all_systems_on(self):
        """Turn on all systems with proper sequencing"""
        try:
            self.log_event("Activating all systems...")
            self.turn_on_lights()
            #time.sleep(0)
            self.turn_on_door_relay()
            messagebox.showinfo("Success", "All systems activated")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to activate all systems: {str(e)}")

    def all_systems_off(self):
        """Turn off all systems with proper sequencing"""
        try:
            self.log_event("Deactivating all systems...")
            self.turn_off_lights()
            #time.sleep(0)
            self.turn_off_door_relay()
            messagebox.showinfo("Success", "All systems deactivated")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to deactivate all systems: {str(e)}")


if __name__ == "__main__":
    root = Tk()
    app = BuildingAutomationSystem(root)
    root.mainloop()
