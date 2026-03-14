# WatchTower – Infrastructure Monitoring & Alert Management System

WatchTower is a lightweight infrastructure monitoring tool built in Python that tracks system resource usage such as CPU and memory and generates alerts when predefined thresholds are exceeded.

The project demonstrates the fundamentals of backend monitoring systems used in modern DevOps environments.

---

## Features

- Real-time CPU usage monitoring
- Memory usage tracking
- Threshold-based alert detection
- Logging system for monitoring events
- Modular and extensible architecture

---

## Tech Stack

- Python
- psutil (system monitoring)
- Logging module
- Backend architecture design

---

## Project Structure


watchtower/
│
├── main.py # Entry point for monitoring system
├── monitor.py # Collects system metrics
├── alerts.py # Alert logic based on thresholds
├── config.py # Configuration values
├── logger.py # Logging system for monitoring events
├── requirements.txt
└── README.md


---

## Monitoring Pipeline

WatchTower follows a simple monitoring workflow:

1. The monitoring module collects system metrics such as CPU and memory usage.
2. Metrics are evaluated against predefined threshold values.
3. If abnormal usage is detected, alerts are generated.
4. Monitoring events are logged for observability.

---

## Running the Project

Install dependencies:


pip install -r requirements.txt


Run the monitoring script:


python main.py


Example output:


System Metrics: {'cpu_usage': 35.2, 'memory_usage': 61.4}


If thresholds are exceeded, alerts will be printed and logged.

---

## Future Improvements

- Real-time monitoring dashboard
- Email or Slack alert integration
- Historical metrics storage
- Container and server monitoring support

---

## Author

Abhigyan Krishna  
Computer Science Engineering Student  
Backend Systems & AI Enthusiast
## Future Improvements

- Real-time monitoring dashboard
- Email / Slack alerts
- Historical metrics storage
