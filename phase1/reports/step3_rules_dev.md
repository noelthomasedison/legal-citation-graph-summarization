# Step 3 — rule extractor, DEV scores

- Dev passages: 5,287 | predicted edges: 2,768
- Resolver: unresolved mentions=337, ambiguous-suffix drops=115

## NESTED credit
- ALL:      P=0.267  R=0.886  F1=0.410   (pred=2768, gold=840)
- Internal  P=0.236  R=0.959  F1=0.379   (pred=2768, gold=688)   (recall-oriented)
- External  P=0.030  R=0.553  F1=0.058   (pred=2768, gold=152)   (recall-oriented)

## EXACT only
- ALL:      P=0.265  R=0.881  F1=0.408   (pred=2768, gold=840)
- Internal  P=0.235  R=0.953  F1=0.377   (pred=2768, gold=688)   (recall-oriented)
- External  P=0.030  R=0.553  F1=0.058   (pred=2768, gold=152)   (recall-oriented)

## NESTED + source-nested credit
- ALL:      P=0.269  R=0.896  F1=0.414   (pred=2768, gold=840)
- Internal  P=0.238  R=0.969  F1=0.382   (pred=2768, gold=688)   (recall-oriented)
- External  P=0.031  R=0.566  F1=0.060   (pred=2768, gold=152)   (recall-oriented)

## Error pools (dev)
- False negatives (gold not covered): 96
    - [Internal] src doc 2, ref `10.3.2(4)` -> 2:10.3.2.4
    - [Internal] src doc 4, ref `2.1(c)` -> 4:2.1
    - [Internal] src doc 4, ref `4.1` -> 4:3.4.1
    - [Internal] src doc 4, ref `4.1` -> 4:3.4.1
    - [External] src doc 4, ref `9.4.2(1)(b)` -> 6:part 4.9.4.2.1
    - [External] src doc 4, ref `9.4.2(2)(b)` -> 6:part 4.9.4.2.2
    - [External] src doc 7, ref `189` -> 17:part 15.189
    - [External] src doc 7, ref `9` -> 17:part 2.chapter 2.9
    - [External] src doc 10, ref `39` -> 17:part 4.39
    - [Internal] src doc 10, ref `3.8.1` -> 10:3.8.1
    - [Internal] src doc 10, ref `4.12.1` -> 10:4.12.1
    - [External] src doc 10, ref `8.11` -> 7:8.8.11
- False positives (no gold match — may include gold-curation misses): 2030
    - doc 2 `Rule 1.7.1` -> 2:1.7.1
    - doc 2 `Rule 2.2.2` -> 2:2.2.2
    - doc 2 `Rule 2.2.3` -> 2:2.2.3
    - doc 2 `Rule 2.2.4` -> 2:2.2.4
    - doc 2 `Rule 2.2.5` -> 2:2.2.5
    - doc 2 `Rule 2.2.4(1)` -> 2:2.2.4.(1)
    - doc 2 `Rule 2.2.6(1)` -> 2:2.2.6.(1)
    - doc 2 `Rule 1.7.2` -> 2:1.7.2
    - doc 2 `Rule 2.3` -> 2:2.3
    - doc 2 `Rule 2.3.1(2)(b)` -> 2:2.3.1.(2)
    - doc 2 `Rule 2.3` -> 2:2.3
    - doc 2 `Rule 7.2.3(b)` -> 2:7.2.3
