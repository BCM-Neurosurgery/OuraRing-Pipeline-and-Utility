# OuraRing-Pipeline-and-Utility
This code pulls information from Oura Ring API V2 and percept LFP data, and outputs json files with the data compiled for further analysis. 
To run the code on your system, you need to modify the config json file with your system's file path to the Percept LFP data, as well as patient specific oura information. This information may also be retrieved from tortugas.

Once json files are collected, sleep_syncronizer.py will sync LFP and Oura data and save the csv.
