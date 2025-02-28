#define PROBLEM "https://judge.u-aizu.ac.jp/onlinejudge/description.jsp?id=0001"

#include <cstdio>
#include <vector>
#include <algorithm>
using namespace std;
#include "../../../marathon/interval_heap.cpp"

int main() {
    vector<int> data;
    for(int i=0; i<10; i++) {
        int height; scanf("%d", &height);
        data.emplace_back(height);
    }

    IntervalHeap<int> heap(data.begin(), data.end());
    for(int i=0; i<3; i++) {
        printf("%d\n", heap.top_max());
        heap.pop_max();
    }
    return 0;
}
