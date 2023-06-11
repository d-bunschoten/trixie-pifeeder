data structure:
  - time feedingtime (00:00 - 23:59)
  - unsigned int portions (> 0)

python libraries:
  - functools (partial)
  - schedule

methods:
  - feed

schedule.every().day.at(time).do(feed(portions))
