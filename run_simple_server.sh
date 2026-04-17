#!/bin/bash
export LD_LIBRARY_PATH=$(pwd)/.libs:$LD_LIBRARY_PATH
python3 simple_websocket_api.py
