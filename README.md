# UBGuardian

[![Latest Version](http://img.shields.io/pypi/v/SpiderKeeper.svg)](https://pypi.python.org/pypi/SpiderKeeper)
[![Python Versions](http://img.shields.io/pypi/pyversions/SpiderKeeper.svg)](https://pypi.python.org/pypi/SpiderKeeper)
[![The MIT License](http://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/DormyMo/SpiderKeeper/blob/master/LICENSE)
   
A scalable admin ui for scrapy spider service 

**UBGuardian** is a fork of [ScrapyKeeper](https://github.com/fliot/ScrapyKeeper) which is a fork of [SpiderKeeper](https://github.com/DormyMo/SpiderKeeper)

Forked to provide:
  - Enhanced statistics (Errors, Exceptions, Retries...)
  - Cache support
  - Dashboarding
  - Most of pending SpideKeeper ahead commits

## Screenshot
![job dashboard](https://github.com/Zephyrrus/UBGuardian/raw/master/screenshot/screenshot_1.png)
![periodic job](https://github.com/Zephyrrus/UBGuardian/raw/master/screenshot/screenshot_2.png)
![project stats](https://github.com/Zephyrrus/UBGuardian/raw/master/screenshot/screenshot_3.png)
![spider stats](https://github.com/Zephyrrus/UBGuardian/raw/master/screenshot/screenshot_4.png)

## Installing
```sh
git clone https://github.com/zephyrrus/UBGuardian.git
cd ScrapyKeeper
pip install .
```

## Deployment
```sh
scrapykeeper -h

Usage: scrapykeeper [options]

Admin ui for scrapy spider service

Options:
  -h, --help            show this help message and exit
  --host=HOST           host, default:0.0.0.0
  --port=PORT           port, default:5000
  --username=USERNAME   basic auth username ,default: admin
  --password=PASSWORD   basic auth password ,default: admin
  --type=SERVER_TYPE    access spider server type, default: scrapyd
  --server=SERVERS      servers, default: ['http://localhost:6800']
  --database-url=DATABASE_URL
                        ScrapyKeeper metadata database default: sqlite://./ScrapyKeeper.db
  --no-auth             disable basic auth
  --no-sentry           disable sentry.io error reporting
  -v, --verbose         log level
```

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/zephyrrus/UBGuardian/tags). 

## Authors

- *Initial work* - [DormyMo](https://github.com/DormyMo)

See also the list of [contributors](https://github.com/DormyMo/SpiderKeeper/contributors) who participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Contributing

Contributions are welcomed!
