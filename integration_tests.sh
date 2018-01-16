#!/usr/bin/env bash

python main.py basic_function.go | lli
if (($? == 42)); then
    echo "Tests pass!"
else
    echo "Test failed!"
fi


python main.py basic_add.go | lli
if (($? == 4)); then
    echo "Tests pass!"
else
    echo "Test failed!"
fi
