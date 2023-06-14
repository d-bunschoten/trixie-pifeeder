data structure:
  - time feedingtime (00:00 - 23:59)
  - unsigned int portions (> 0)

##Installation
`pip install -r requirements.txt`

Update the `app/config.json` file

methods:
  - feed

schedule.every().day.at(time).do(feed(portions))
