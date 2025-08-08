ALGORITHM fibonacci {
    show "Fibonacci Sequence:";

     function fib(n: int) {
        if n < 1 {
            return 0;
        }
        elif n < 3 {
            return 1;
        }
        return fib(n - 1) + fib(n - 2);
    }
    show(fib(90));
 
}
