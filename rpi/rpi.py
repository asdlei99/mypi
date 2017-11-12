#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sakshat import SAKSHAT
import time
import urllib2
import json
import pygame
import os
from tornado.gen import coroutine, Task
from tornado.web import asynchronous


class RasPi():
    SAKS = None
    __dp = True
    __alarm_beep_status = False
    __alarm_beep_times = 0
    __alarm_time = "07:10:00"  # 在这里设定闹钟定时时间

    tellTime = False

    def init(self):
        self.SAKS = SAKSHAT()

        # 在检测到轻触开关触发时自动执行此函数
        def tact_event_handler(pin, status):
            print pin, status
            # 停止闹钟响铃（按下任何轻触开关均可触发）
            self.__alarm_beep_status = False
            self.__alarm_beep_times = 0
            self.SAKS.buzzer.off()
            self.SAKS.ledrow.off_for_index(6)

        self.SAKS.tact_event_handler = tact_event_handler
        self.SAKS.buzzer.off()
        self.SAKS.ledrow.off_for_index(6)

    @coroutine
    def getWeatherData(self):
        weather_url = 'https://free-api.heweather.com/x3/weather?cityid=CN101010400&key=e2dfc339a09c4e09b1e389e9578af294'
        req = urllib2.Request(weather_url)
        resp = urllib2.urlopen(req)
        content = resp.read()
        if content:
            weatherJSON = json.JSONDecoder().decode(content)
            print(content)
            try:
                if weatherJSON['HeWeather data service 3.0'][0]['status'] == "ok":
                    res = weatherJSON['HeWeather data service 3.0'][0]
                    pm10 = str(res['aqi']['city']['pm10'])  # 67
                    pm25 = str(res['aqi']['city']['pm25'])  # 5
                    qlty = res['aqi']['city']['qlty']  # 良
                    suggestion = ''
                    for key in ['air', 'comf', 'cw', 'drsg', 'flu', 'sport', 'trav', 'uv']:
                        suggestion += res['suggestion'][key]['txt']
                    return "空气指数%s,PM10 %s,PM2.5 %s,%s" % (qlty, pm10, pm25, suggestion)
                else:
                    return None
            except Exception as e:
                print e.message
                return None

    @coroutine
    def showTime(self):
        t = time.localtime()
        h = t.tm_hour
        m = t.tm_min
        s = t.tm_sec
        w = time.strftime('%w', t)
        # print h,m,s,w
        # print "%02d:%02d:%02d" % (h, m, s)
        if self.__dp:
            self.SAKS.digital_display.show(("%02d%02d." % (h, m)))
        else:
            self.SAKS.digital_display.show(("%02d%02d" % (h, m)))
        self.__dp = not self.__dp
        return {'localtime': t, 'hour': h, 'min': m, 'sec': s, 'strftime': w}

    @coroutine
    def playTellTime(self, hours):
        path = "%s/saksha/tell-time/%d.mp3" % (os.path.abspath('.'), hours)
        pygame.mixer.init()
        pygame.mixer.music.set_volume(1.0)
        clip = pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        time.sleep(clip.seconds())
        pygame.mixer.quit()
        self.tellTime = False

    @coroutine
    @asynchronous
    def run(self):
        time = yield Task(self.showTime)
        hour = time.get('hour')
        min = time.get('min')
        sec = time.get('sec')
        if 21 >= hour >= 7 and min == 0 and not self.tellTime:
            self.tellTime = True
            yield Task(self.playTellTime, time.get('hour'))

        if ("%02d:%02d:%02d" % (hour, min, sec)) == self.__alarm_time:
            self.__alarm_beep_status = True
            self.__alarm_beep_times = 0

        if self.__alarm_beep_status:
            self.SAKS.buzzer.on()
            self.SAKS.ledrow.on_for_index(6)
            self.__alarm_beep_times += 1
            # 30次没按下停止键则自动停止闹铃
            if self.__alarm_beep_times > 30:
                self.SAKS.buzzer.off()
                self.SAKS.ledrow.off_for_index(6)
                self.__alarm_beep_status = False
                self.__alarm_beep_times = 0

        leds = sec % 10
        if hour > 21 or (-1 < hour < 7):
            if leds >= 8:
                self.SAKS.ledrow.off()
            else:
                self.SAKS.ledrow.on_for_index(leds)
        else:
            self.SAKS.ledrow.off()