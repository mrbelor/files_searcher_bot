#include <iostream>
#include <vector>
#include <string>
using std::vector;
using std::string;


vector<int> _kmpPrefix(const vector<string>& needle) {
    int m = static_cast<int>(needle.size());
    vector<int> lps(m, 0);
    int j = 0;
    for (int i = 1; i < m; ++i) {
        while (j > 0 && needle[i] != needle[j]) {
            j = lps[j - 1];
        }
        if (needle[i] == needle[j]) {
            ++j;
        }
        lps[i] = j;
    }
    return lps;
}

// Ищет все индексы совпадений подсписка needle в haystack
vector<int> kmpSearch(const vector<string>& haystack,
                           const vector<string>& needle) {
    int n = static_cast<int>(haystack.size());
    int m = static_cast<int>(needle.size());
    if (m == 0 || n < m) {
        return {};
    }
    vector<int> lps = _kmpPrefix(needle);
    vector<int> res;
    int j = 0;
    for (int i = 0; i < n; ++i) {
        while (j > 0 && haystack[i].find(needle[j]) == string::npos) {
            j = lps[j - 1];
        }
        if (haystack[i].find(needle[j]) != string::npos) {
            ++j;
            if (j == m) {
                int start = i - m + 1;
                for (int k = start; k < start + m; ++k) {
                    res.push_back(k);
                }
                j = lps[j - 1];
            }
        }
    }
    return res;
}


int main() {
    
    vector<string> haystack = {"aaa", "aaa", "aaa", "aaa"};
    vector<string> needle = {"aa", "aa"};
    
    vector<int> indices = kmpSearch(haystack, needle);
    for (int idx : indices) {
        std::cout << idx << " ";
    }
    // Вывод: 0 1 2 3
    return 0;
}

