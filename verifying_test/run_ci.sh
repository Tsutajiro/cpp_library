#!/bin/bash
set -e

# you can install oj with: $ pip3 install --user -U online-judge-tools=='6.*'
which oj > /dev/null

CXX=${CXX:-g++}
CXXFLAGS="${CXXFLAGS:--std=c++14 -O3}"
ulimit -s 65532

list-dependencies() {
    file="$1"
    $CXX $CXXFLAGS -I . -MD -MF /dev/stdout -MM "$file" | sed '1s/[^:].*: // ; s/\\$//' | xargs -n 1
}

list-defined() {
    file="$1"
    $CXX $CXXFLAGS -I . -dM -E "$file"
}

get-url() {
    file="$1"
    list-defined "$file" | grep '^#define PROBLEM ' | sed 's/^#define PROBLEM "\(.*\)"$/\1/'
}

get-error() {
    file="$1"
    list-defined "$file" | grep '^#define ERROR ' | sed 's/^#define ERROR "\(.*\)"$/\1/'
}

get-last-commit-date() {
    file="$1"
    list-dependencies "$file" | xargs git log -1 --date=iso --pretty=%ad
}

is-verified() {
    file="$1"
    cache=test/timestamp/$(echo -n "$file" | md5sum | sed 's/ .*//')
    timestamp="$(get-last-commit-date "$file")"
    [[ -e $cache ]] && [[ $timestamp = $(cat $cache) ]]
}

mark-verified() {
    file="$1"
    cache=test/timestamp/$(echo -n "$file" | md5sum | sed 's/ .*//')
    mkdir -p test/timestamp
    timestamp="$(get-last-commit-date "$file")"
    echo $timestamp > $cache
}

list-recently-updated() {
    for file in $(find . -name \*.test.cpp) ; do
        list-dependencies "$file" | xargs -n 1 | while read f ; do
            git log -1 --format="%ci	${file}" "$f"
        done | sort -nr | head -n 1
    done | sort -nr | head -n 20 | cut -f 2
}

run() {
    file="$1"
    url="$(get-url "$file")"
    dir=test/$(echo -n "$url" | md5sum | sed 's/ .*//')
    mkdir -p ${dir}

    # ignore if IGNORE is defined
    if list-defined "$file" | grep '^#define IGNORE ' > /dev/null ; then
        return
    fi

    if ! is-verified "$file" ; then
        # compile
        $CXX $CXXFLAGS -I . -o ${dir}/a.out "$file"
        if [[ -n ${url} ]] ; then
            # download
            if [[ ! -e ${dir}/test ]] ; then
                sleep 2
                oj download --system "$url" -d ${dir}/test
            fi
            # test with tolerance error
            if list-defined "$file" | grep '^#define ERROR ' > /dev/null ; then
                error=$(get-error "$file")
                oj test -e ${error} -c ${dir}/a.out -d ${dir}/test
            else
                oj test -c ${dir}/a.out -d ${dir}/test
            fi
        else
            # run
            ${dir}/a.out
        fi
        mark-verified "$file"
    fi
}

# CI
git remote set-url origin https://Tsutajiro:${GITHUB_TOKEN}@github.com/Tsutajiro/cpp_library.git
git config --global user.name "Tsutajiro"
git config --global user.email "y.sugie.15739d@gmail.com"
git config --global push.default simple
git branch -a

for f in $(find . -name \*.test.cpp) ; do
    echo "----------------------------------------------------------------------"
    echo "## Testing '${f}' ..."
    echo "----------------------------------------------------------------------"
    run $f
done

git status -s
if [ -n "$(git status -s)" ]; then
    last_commit="$(git log -1 | head -1 | awk '{print $2}')"
    git add ./test
    git commit -m "[auto-verifier] verify commit ${last_commit}"
    echo 'passed until this section'
    git push --quiet origin HEAD >/dev/null 2>&1
fi

# if [[ $# -eq 0 ]] ; then
#     if [[ $CI ]] ; then
#         # CI
#         for f in $(list-recently-updated | grep aoj) ; do
#             run $f
#         done
#     else
#         # # local / github actions
#         git config --local user.name "Tsutajiro"
#         git config --local user.email "y.sugie.15739d@gmail.com"
#         git branch -a

#         for f in $(find . -name \*.test.cpp) ; do
#             echo "----------------------------------------------------------------------"
#             echo "## Testing '${f}' ..."
#             echo "----------------------------------------------------------------------"
#             run $f
#         done

#         git status -s
#         if [ -n "$(git status -s)" ]; then
#             last_commit="$(git log -1 | head -1 | awk '{print $2}')"
#             git add ./test
#             git commit -m "[auto-verifier] verify commit ${last_commit}"
#             git push --quiet origin HEAD >/dev/null 2>&1
#         fi
#     fi
# else
#     # specified
#     for f in "$@" ; do
#         run "$f"
#     done
# fi
