#!/usr/bin/env bash
# $@ refers to all arguments and allow us to pass examples/consts/*.c as argument
for i in "$@"
do  
    echo "$i"
    clang -emit-llvm -S $i -o /dev/stdout | lli            #compile with clang to llvm IR and run 
    expected=$?             #get exit code
    python main.py $i | lli              #compile to llvm IR and run
    actual=$?                #get exit code
    echo -n "$i:    "
    if [ "$expected" -ne "$actual" ]
    then
        echo "FAIL"
    else
        echo "OK"
    fi
done

#cleanup
#rm a.out
