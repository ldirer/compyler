Code for my experiments at writing a C compiler in Python.  

It compiles to LLVM Intermediate Representation and handles if statements, for loops, function definitions and calls as well as basic operations.

* The goal was to figure out how a compiler works. I feel like I achieved a good part of this, although you could spend years writing a compiler.
* I do not consider the code very clean. I kinda like some of the hacks in it but you might not share these feelings. 
* The hard part for me was coming up with the grammar on my own, because I was trying to force these two **incompatible** things: 

    * I wanted a simple parser (like the one I have).
    * I wanted a clean, easy-to-read grammar (unlike the one I have).
        
One of the reasons is that my parser does not handle left-recursion.  

About the code:

* I don't really have a separate lexer step. I did not really feel it was necessary with the design I chose.  
* My parser does not give explicit errors. Though it's not straightforward to give good error messages, some improvements would definitely help.


## You want to learn how to write a C compiler

This is probably not the best repo for this.  
I got you covered though with this great tutorial series: 
[https://norasandler.com/2017/11/29/Write-a-Compiler.html](https://norasandler.com/2017/11/29/Write-a-Compiler.html)

I stole examples and the `.c` test cases files from there ~~and deleted the ones that I found too annoying to implement~~.
