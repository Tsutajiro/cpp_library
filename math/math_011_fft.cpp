// FFT (高速フーリエ変換)
// Verified: 高速フーリエ変換 (ATC 001 C)

using Complex = complex<double>;
vector<Complex> dft(vector<Complex> A, int N, int sgn = 1) {
    for(int i=0, j=1; j<N-1; j++) {
        for(int k=N >> 1; k>(i ^= k); k >>= 1);
        if(j < i) swap(A[i], A[j]);
    }

    for(int m=2; m<=N; m*=2) {
        Complex zeta(cos(2.0 * M_PI / m), sin(2.0 * M_PI / m) * sgn);

        for(int i=0; i<N; i+=m) {
            Complex zeta_pow = 1;
            for(int u=i, v=i+m/2; v<i+m; u++, v++) {
                Complex vl = A[u], vr = zeta_pow * A[v];
                A[u] = vl + vr;
                A[v] = vl - vr;
                zeta_pow = zeta_pow * zeta;
            }
        }
    }
    return A;
}

vector<Complex> inv_dft(vector<Complex> A, int N) {
    A = dft(A, N, -1);
    for(int i=0; i<N; i++) {
        A[i] /= N;
    }
    return A;
}

vector<Complex> multiply(vector<Complex> A, vector<Complex> B) {
    int sz = A.size() + B.size() + 1;
    int N = 1; while(N < sz) N *= 2;

    A.resize(N), B.resize(N);
    A = dft(A, N), B = dft(B, N);

    vector<Complex> F(N);
    for(int i=0; i<N; i++) {
        F[i] = A[i] * B[i];
    }
    return inv_dft(F, N);
}
