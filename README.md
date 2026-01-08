# AI-Based Traffic Matrix Prediction for SDN

This project implements a Traffic Matrix Prediction solution for Software-Defined Networks (SDN) using Deep Learning. It integrates a custom Mininet topology with a Ryu controller to collect real-time traffic data and uses LSTM, Bi-LSTM, and GRU models to predict future traffic patterns.

## 🚀 Features

*   **SDN Simulation:** Custom Mininet topology (`topo_final.py`) with 14 hosts and switches.
*   **Traffic Management:** Ryu SDN controller (`controller_final.py`) for flow rule installation and traffic monitoring.
*   **Traffic Generation:** Automated traffic generation script (`traffic-gen-script.sh`) using `tcpreplay` and prepared PCAP files.
*   **Deep Learning Models:**
    *   **LSTM (Long Short-Term Memory)**
    *   **Bi-LSTM (Bidirectional LSTM)**
    *   **GRU (Gated Recurrent Unit)**
    *   Models are trained to predict traffic matrices based on historical data.

## 📂 Project Structure

```
.
├── Model-training.ipynb        # Jupyter notebook for training and evaluating DL models
├── mininet/
│   ├── topo_final.py           # Custom Mininet topology script
│   ├── traffic-gen-script.sh   # Bash script for generating network traffic
│   └── ...
├── ryu/
│   ├── controller_final.py     # Ryu controller application
│   └── ...
├── prepared-pcaps/             # Directory containing traffic data (PCAPs) for hosts
└── output_data1.csv            # Example dataset/output (if applicable)
```

## 🛠 Prerequisites

*   **Python 3.x**
*   **Mininet**
*   **Ryu SDN Controller**
*   **TensorFlow / Keras**
*   **tcpreplay**
*   **NumPy, Pandas, Matplotlib, Scikit-learn**

## 🔧 Installation & Usage

### 1. Network Simulation (Mininet & Ryu)

1.  **Start the Ryu Controller:**
    Open a terminal and run the Ryu controller application.
    ```bash
    ryu-manager ryu/controller_final.py
    ```
    *Note: You may need to specify an output file for traffic data using an environment variable if configured in the script.*

2.  **Start the Mininet Topology:**
    Open a new terminal (as root/sudo) and start the custom topology.
    ```bash
    sudo python3 mininet/topo_final.py
    ```
    This script builds the network, connects to the remote controller, and starts traffic generation replays from `prepared-pcaps`.

### 2. Traffic Generation

The `mininet/topo_final.py` script automatically triggers traffic replay. Alternatively, you can manually run the generation script from within the Mininet environment or on the host if network namespaces are handled correctly.

```bash
# Inside Mininet CLI or appropriate context
./mininet/traffic-gen-script.sh
```

### 3. Model Training & Prediction

1.  **Prepare Dataset:** Ensure your traffic data CSV (e.g., `testbed_flat_tms.csv`) is in the correct location (`../dataset/` as referenced in the notebook).
2.  **Run the Notebook:**
    Launch Jupyter Notebook to train and evaluate the models.
    ```bash
    jupyter notebook Model-training.ipynb
    ```
3.  **Train Models:** Execute the cells to:
    *   Load and preprocess the dataset.
    *   Train LSTM, Bi-LSTM, and GRU models.
    *   Visualize loss and prediction accuracy.

## 📊 Results

The project compares the performance of Vanilla LSTM, Bi-LSTM, and GRU models in predicting Origin-Destination (OD) traffic flows. The notebook contains visualization of loss curves and prediction results.

---
*Created for ACN Project - BITS Pilani*
