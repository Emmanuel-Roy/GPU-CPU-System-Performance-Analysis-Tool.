# GPU-System-Performance-Analysis-Tool.

A Python-based GUI to interface and display **real-time systemperformance metrics** from: 
  - **Nvidia NVML** (GPU Utilization, VRAM, Power, Temperature, etc.)
  - **Intel PresentMon** (Frame Times, GPU Busy per frame)
  - **psutil** (CPU usage, CPU interrupts, RAM usage, process monitoring)
    
<img width="3116" height="1437" alt="image" src="https://github.com/user-attachments/assets/f9960684-20e3-42dc-974f-f2cc6e9d77fd" />

## About.

-   Built to display metrics on an **ultrawide 21:9 monitor** while running 16:9 games, without covering game screen space.
-   Exposes **extra statistics** like **CPU interrupts** and **GPU Busy** not typically available in MSI Afterburner or Steam overlay.
-   Brings **all system and frame metrics into one easy-to-use tool** with real-time graphs and CSV logging.

## How to use.
1.  **Download PresentMon**
  - Get the latest [PresentMon release](https://github.com/GameTechDev/PresentMon).
  - Rename the ".exe" to 'PresentMon.exe' and place it inside the PresentMon folder.
2.  **Install Dependencies**
``` 
pip install psutil matplotlib pynvml
```
3.  **Run the Overlay**
```
python main.py
```

## Bugs / Issues
- Sometimes PresentMon doesn't want to start, i've found that restarting your computer will usually fix this.
- Currently only Nvidia GPU's are supported, but I've seen that there are drop in replacements for NVML if you would like to use an AMD GPU.
