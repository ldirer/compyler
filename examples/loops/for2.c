int main() {
    // declaration of variable before the loop
    int i;
    int j = 0;

    for (i = 0; i < 5; i = i + 1) {
        j = j + 2;
    }
    return j;
}