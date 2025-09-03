import subprocess
import psutil
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
from pynvml import *
import os
import csv
import datetime
import time

# ---------------- CONFIG ----------------

PresentMon_path = r"PresentMon/PresentMon.exe"  # Default Path.

Data_points = 60

CPU_core_cnts = psutil.cpu_count(logical=True) # Shouldn't change during run time.

# ---------------- DATA QUEUES ----------------

CPU_usage_queue = [deque([0]*Data_points, maxlen=Data_points) for _ in range(CPU_core_cnts)]
CPU_interrupt_queue = deque([0]*Data_points, maxlen=Data_points)
GPU_busy_queue = deque([0]*Data_points, maxlen=Data_points)
GPU_Utilization_queue = deque([0]*Data_points, maxlen=Data_points)
VRAM_queue = deque([0]*Data_points, maxlen=Data_points)
GPU_power_queue = deque([0]*Data_points, maxlen=Data_points)
GPU_Temperatures_queue = deque([0]*Data_points, maxlen=Data_points)
RAM_queue = deque([0]*Data_points, maxlen=Data_points)
FrameTime_queue = deque([0]*Data_points, maxlen=Data_points)

# CPU Interrupts are handled a little differently. 
CPU_interrupt_history = psutil.cpu_stats().interrupts

# ---------------- MATPLOTLIB SETUP ----------------

fig, axes = plt.subplots(10, 1, figsize=(12, 18)) 
plt.subplots_adjust(hspace=1.5) 

(CPU_usage_plot, CPU_interrupts_plot, GPU_busy_plot, GPU_Utilization_plot, VRAM_plot,
 GPU_power_plot, GPU_Temp_plot, RAM_plot, FrameTime_plot, Process_information_plot) = axes

# CPU usage
CPU_usage_data = [CPU_usage_plot.plot([], [], label=f"Core {i}")[0] for i in range(CPU_core_cnts)]
CPU_usage_plot.set_title("CPU Usage (%) per Core")
CPU_usage_plot.set_ylim(0, 100)
CPU_usage_plot.set_xlim(0, Data_points)
CPU_usage_plot.legend(loc="upper right", ncol=4, fontsize=7)
CPU_usage_plot.grid(True)

# CPU interrupts
CPU_interrupts_data, = CPU_interrupts_plot.plot([], [], color="red")
CPU_interrupts_plot.set_title("CPU Interrupts (Overall)")
CPU_interrupts_plot.set_ylim(0, 10)
CPU_interrupts_plot.set_xlim(0, Data_points)
CPU_interrupts_plot.grid(True)

# GPU Busy
GPU_busy_data, = GPU_busy_plot.plot([], [], color="red")
GPU_busy_plot.set_title("GPU Busy (ms per frame)")
GPU_busy_plot.set_ylim(0, 10)
GPU_busy_plot.set_xlim(0, Data_points)
GPU_busy_plot.grid(True)

# GPU Util
GPU_Utilization_data, = GPU_Utilization_plot.plot([], [], color="orange")
GPU_Utilization_plot.set_title("GPU Util (%)")
GPU_Utilization_plot.set_ylim(0, 100)
GPU_Utilization_plot.set_xlim(0, Data_points)
GPU_Utilization_plot.grid(True)

# VRAM
VRAM_data, = VRAM_plot.plot([], [], color="purple")
VRAM_plot.set_title("GPU VRAM (%)")
VRAM_plot.set_ylim(0, 100)
VRAM_plot.set_xlim(0, Data_points)
VRAM_plot.grid(True)

# GPU Power
GPU_power_data, = GPU_power_plot.plot([], [], color="magenta")
GPU_power_plot.set_title("GPU Power (Watts)")
GPU_power_plot.set_ylim(0, 400)
GPU_power_plot.set_xlim(0, Data_points)
GPU_power_plot.set_yticks(range(0, 401, 50))
GPU_power_plot.grid(True)

# GPU Temp
GPU_Temp_data, = GPU_Temp_plot.plot([], [], color="brown")
GPU_Temp_plot.set_title("GPU Temp (°C)")
GPU_Temp_plot.set_ylim(0, 100)
GPU_Temp_plot.set_xlim(0, Data_points)
GPU_Temp_plot.grid(True)

# RAM
RAM_data, = RAM_plot.plot([], [], color="green")
RAM_plot.set_title("RAM Usage (GB)")

RAM_Labels = [4, 8, 12, 16, 20, 24, 28, 32] # Change based on your system.

RAM_plot.set_yticks(RAM_Labels)
RAM_plot.set_yticklabels(RAM_Labels)
RAM_plot.set_ylim(0, 32)
RAM_plot.set_xlim(0, Data_points)
RAM_plot.grid(True)

# Frame Time
FrameTime_data, = FrameTime_plot.plot([], [], color="blue")
FrameTime_plot.set_title("Frame Time (ms)")
FrameTime_plot.set_ylim(0, 50)
FrameTime_plot.set_xlim(0, Data_points)
FrameTime_plot.grid(True)

# Get GPU Statistics through GPU NVML (ONLY WORKS FOR NVIDIA)
try:
    nvmlInit()
    Current_GPU = nvmlDeviceGetHandleByIndex(0)
    GPU_power_NVML_max = nvmlDeviceGetEnforcedPowerLimit(Current_GPU) / 1000
    if GPU_power_NVML_max and GPU_power_NVML_max > 0:
        GPU_power_plot.set_ylim(0, GPU_power_NVML_max*1.2)
except NVMLError as e:
    print("NVML init failed:", e)
    Current_GPU = None

def get_gpu_nvml(Current_GPU):
    if Current_GPU is None: # (OBV IF NO GPU NO STATS)
        return 0, 0, 0, 0
    try: # Convert NVML to proper stats we care about.
        Util = nvmlDeviceGetUtilizationRates(Current_GPU)
        Mem = nvmlDeviceGetMemoryInfo(Current_GPU)
        Power_mW = nvmlDeviceGetPowerUsage(Current_GPU)
        Temp = nvmlDeviceGetTemperature(Current_GPU, NVML_TEMPERATURE_GPU)
        return Util.gpu, Mem.used/Mem.total*100, Power_mW/1000, Temp
    except NVMLError:
        return 0, 0, 0, 0 # If there's an error don't show GPU stats

# ---------------- Setup PresentMon and get data ----------------

def run_dashboard():
    global CPU_interrupt_history
    Monitoring_target = input("Enter application name (YourGame.exe): ")

    # wait for process
    print(f"Waiting for application to start {Monitoring_target}...")
    pid = None
    while pid is None:
        for p in psutil.process_iter(['name', 'pid']):
            if p.info['name'] == Monitoring_target:
                pid = p.info['pid']
                break
        time.sleep(1)

    print(f"Application detected with PID {pid}. Starting PresentMon...")

    os.makedirs("logs", exist_ok=True) # Create folder to store .csv if it doesn't exist.
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/dashboard_{timestamp_str}_pid{pid}.csv"
    csv_handle = open(log_file, 'w', newline='')
    csv_writer = csv.writer(csv_handle) # Send stastical output to the .csv file.

    header = ["Timestamp"] + [f"CPU_Core_{i}_Usage" for i in range(CPU_core_cnts)] + \
             ["CPU_Interrupts"] + \
             ["GPU_Busy_ms","GPU_Util","GPU_VRAM_%","GPU_Power_W","GPU_Temp","RAM_GB","FrameTime_ms"]
    csv_writer.writerow(header)

    session_name = f"DashSession_{pid}_{int(time.time())}"
    pm_proc = subprocess.Popen(
        [PresentMon_path, "--output_stdout", "--v2_metrics", "--process_id", str(pid),
         "--session_name", session_name, "--stop_existing_session"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1
    )

    # Read PresentMon data. (Header)
    PM_header = []
    Start_time = time.time()
    
    while True:
        line = pm_proc.stdout.readline()
        if line:
            line = line.strip()
            if line:
                PM_header = line.split(",")
                if any("FrameTime" in c or "GPU" in c for c in PM_header):
                    break
        if time.time() - Start_time > 15:
            pm_proc.kill()
            raise RuntimeError("PresentMon CSV header not detected. Try restarting your PC.")

    GPU_busy_index = next((i for i, c in enumerate(PM_header) if "GPUBusy" in c), None)
    FrameTime_index = next((i for i, c in enumerate(PM_header) if "FrameTime" in c), None)

    
    def update(frame):
        global CPU_interrupt_history

        # CPU usage
        cpu_percent = psutil.cpu_percent(percpu=True)
        for i in range(CPU_core_cnts):
            CPU_usage_queue[i].append(cpu_percent[i] if i < len(cpu_percent) else 0)

        # CPU interrupts
        Current_interrupts = psutil.cpu_stats().interrupts
        Interrupts_change = Current_interrupts - CPU_interrupt_history
        CPU_interrupt_history = Current_interrupts
        CPU_interrupt_queue.append(Interrupts_change)
        CPU_interrupts_plot.set_ylim(0, max(max(CPU_interrupt_queue)*1.2, 10))

        # RAM usage
        RAM_usage = (psutil.virtual_memory().total - psutil.virtual_memory().available) / 1024**3
        RAM_queue.append(RAM_usage)

        # GPU stats
        GPU_Utilization_NVML, VRAM_use_NVML, GPU_power_NVML, GPU_Temp_NVML = get_gpu_nvml(Current_GPU)
        GPU_Utilization_queue.append(GPU_Utilization_NVML)
        VRAM_queue.append(VRAM_use_NVML)
        GPU_power_queue.append(GPU_power_NVML)
        GPU_Temperatures_queue.append(GPU_Temp_NVML)

        # PresentMon line (If not currently being read, replace with 0.)
        line = pm_proc.stdout.readline().strip()
        if line and not line.startswith("Application"):
            parts = line.split(",")
            try:
                if GPU_busy_index is not None:
                    busy = float(parts[GPU_busy_index])
                    GPU_busy_queue.append(min(max(busy,0.0),10.0))
                else:
                    GPU_busy_queue.append(0.0)

                if FrameTime_index is not None:
                    ft = float(parts[FrameTime_index])
                    FrameTime_queue.append(ft)
                else:
                    FrameTime_queue.append(0.0)
            except:
                GPU_busy_queue.append(0.0)
                FrameTime_queue.append(0.0)

        # Update data lines with new data points.
        x = range(Data_points)
        for i, l in enumerate(CPU_usage_data):
            l.set_data(x, list(CPU_usage_queue[i]))
        CPU_interrupts_data.set_data(x, list(CPU_interrupt_queue))
        GPU_busy_data.set_data(x, list(GPU_busy_queue))
        GPU_Utilization_data.set_data(x, list(GPU_Utilization_queue))
        VRAM_data.set_data(x, list(VRAM_queue))
        GPU_power_data.set_data(x, list(GPU_power_queue))
        GPU_Temp_data.set_data(x, list(GPU_Temperatures_queue))
        RAM_data.set_data(x, list(RAM_queue))
        FrameTime_data.set_data(x, list(FrameTime_queue))

        # PID/EXE/Date info for the bottom right corner (kinda useless, but i think its cool)
        Process_information_plot.clear()
        Process_information_plot.axis('off')
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        Process_information_plot.text(0, 0.7, f"PID: {pid}", fontsize=12)
        Process_information_plot.text(0, 0.5, f"EXE: {Monitoring_target}", fontsize=12)
        Process_information_plot.text(0, 0.3, f"Time: {current_time}", fontsize=12)

        # CSV logging to file.
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        row = [timestamp] + [CPU_usage_queue[i][-1] for i in range(CPU_core_cnts)]
        row += [CPU_interrupt_queue[-1]]
        row += [GPU_busy_queue[-1], GPU_Utilization_queue[-1], VRAM_queue[-1], GPU_power_queue[-1],
                GPU_Temperatures_queue[-1], RAM_queue[-1], FrameTime_queue[-1]]
        csv_writer.writerow(row)
        csv_handle.flush()

        return [*CPU_usage_data, CPU_interrupts_data, GPU_busy_data, GPU_Utilization_data, VRAM_data,
                GPU_power_data, GPU_Temp_data, RAM_data, FrameTime_data]

    try:
        ani = animation.FuncAnimation(fig, update, interval=1000, blit=False, cache_frame_data=False)
        plt.tight_layout()
        plt.show()
    finally: # Kill PresentMon and NVML.
        pm_proc.kill()
        if Current_GPU is not None:
            nvmlShutdown()
        csv_handle.close()

if __name__ == "__main__":
    run_dashboard()
