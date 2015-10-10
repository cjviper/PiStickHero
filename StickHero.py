#! /home/pi/.virtualenvs/cv/bin/python
import cv2
import numpy as np
import time
import picamera
import RPi.GPIO as GPIO

class StickHero:
    
    def __init__(self):
        self.camera = picamera.PiCamera()
        self.camera.vflip=True
        self.camera.hflip=True
        self.camera.resolution=(1152,720)
        self.camera.brightness=70
        self.camera.contrast=80
        self.cornerThreshold = 20
        self.contrast = 65.0/50
        self.brightness = 0.0# 10.0
        self.blockSize = 2
        self.kernelSize = 5
        self.k = 0.03
        self.harrisThreshold = 0.10#0.20
        self.count = 0
        self.waitTime = 5
        self.man = cv2.imread('man.png')
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(2, GPIO.OUT)
        GPIO.output(2, GPIO.LOW)
    
    def __del__(self):
        self.camera.close()
    
    def findMan(self,img):
        print('finding man')
        imgCopy=img.copy()
        manWidth, manHeight = self.man.shape[:2]
        match = cv2.matchTemplate(img, self.man, cv2.TM_CCOEFF_NORMED)
        minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(match)
        topLeft = maxLoc
        bottomRight = (topLeft[0]+manWidth, topLeft[1]+manHeight)
        cv2.rectangle(imgCopy, topLeft, bottomRight, 255, 2)
        cv2.imwrite('man'+str(self.count)+'.jpg', imgCopy)
        return (topLeft, bottomRight)

    def getRoi(self,img, manPos):
        roi = img[(manPos[1]-10):(manPos[1]+16), (manPos[0]-10):(manPos[0]+500)]
        return roi

    def adjustBrightnessContrast(self,img):
        img = cv2.multiply(img,np.array([self.contrast]))
        img = cv2.add(img,np.array([self.brightness]))
        return img
        
    def findCornersHarris(self,img):
        print('detecting corners')
        imgCopy=img[:,15:].copy()
        cv2.imwrite('roi'+str(self.count)+'.jpg', imgCopy)
        imgGrey=cv2.cvtColor(imgcopy, cv2.COLOR_BGR2GRAY)
        corners=cv2.cornerHarris(imgGrey, self.blockSize, self.kernelSize, self.k)
        bestCorners=np.where(corners > self.harrisThreshold * corners.max())
        bestCorners=[(x,y) for x,y in zip(bestCorners[1], bestCorners[0])]
        corners=cv2.dilate(corners, None)
        imgCorners=imgCopy.copy()
        imgCorners[corners > self.harrisThreshold*corners.max()] = [0,0,255]
        cv2.imwrite('hcorners'+str(self.count)+'.jpg', imgCorners)
        dists=[c[0] for c in bestCorners]
        maxX, minX = max(dists), min(dists)
        print(minX, maxX)
        maxPt = [c for c in bestCorners if c[0] == maxX][0]
        minPt = [c for c in bestCorners if c[0] == minX][0]   
        return bestCorners
    
    def selectCorners(self, corners, margin=3):
        corners = sorted(corners, key=lambda x:-x[0])
        for c in corners:
            partners = [c1 for c1 in corners if abs(c1[1] - c[1]) <= margin]
            if len(partners) > 0:
                minX = min([p[0] for p in partners])
                leftCorner = [p for p in partners if p[0] == minX][0]
                return (leftCorner, c)
        return None
    
    def getImage(self):
        print 'getting image'
        img = self.camera.capture('image'+str(self.count)+'.jpg')
        img = cv2.imread('image'+str(self.count)+'.jpg')
        return img[200:600, 400:1000]
           
    def getDistance(self, corners):
        dists=[c[0] for c in corners]
        left, right = min(dists), max(dists)
        dist = (left + right)/2.0
        return dist
        
    def activateSolenoid(self, distance):
        rate = 388.0 #390.0 #430.0
        const = 0.0
        delay = (distance+13)/rate + const
        print 'delay=' + str(delay)
        print 'activating'
        GPIO.output(2, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(2, GPIO.LOW)
        
    def go(self):
        while(1):
            print '--- count = '+str(self.count) + ' ---'
            img = self.getImage()
            topLeft, bottomRight = self.findMan(img[:,0:260])
            roi = self.getRoi(img, bottomRight)
            roi = self.adjustBrightnessContrast(roi)
            hcorners = self.findCornersHarris(roi)
            if len(hcorners) == 0:
                continue
            selectedCorners = self.selectCorners(hcorners, 3)
            print(selectedCorners)
            if selectedCorners==None:
                continue
            dist = self.getDistance(selectedCorners)
            print('distance='+str(dist))
            if dist <= 0:
                continue
            self.activateSolenoid(dist)
            self.count+=1
            time.sleep(self.waitTime)
            print ''
    
sh = StickHero()
sh.go()


