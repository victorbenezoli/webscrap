from pytesseract import image_to_string
from PIL import Image, ImageOps, ImageFilter
import re

class resolve_captcha:

    def __init__(self, image, thresholds=110, psm=7):
        self.image = Image.open(image)
        self.thresholds = thresholds
        self.psm = psm

    def __prepare_image(self):
        image = self.image
        """Transform image to greyscale and blur it"""
        image = image.filter(ImageFilter.SMOOTH_MORE)
        image = image.filter(ImageFilter.SMOOTH_MORE)
        if 'L' != image.mode:
            image = image.convert('L')
        return image

    def __remove_noise(self):
        image = self.image
        for column in range(image.size[0]):
            for line in range(image.size[1]):
                value = self.__remove_noise_by_pixel(column, line)
                image.putpixel((column, line), value)
        return image

    def __remove_noise_by_pixel(self, column, line):
        image, thresholds = self.image, self.thresholds
        if image.getpixel((column, line)) < thresholds:
            return (0)
        return (255)

    def text_from_captcha(self):
        self.image = self.__prepare_image()
        image = self.__remove_noise()
        lang = 'eng'
        config = '--oem 1 --psm {} -c page_separator='.format(self.psm)
        captcha = image_to_string(image, lang=lang, config=config)
        captcha = re.sub('\W+', '', captcha.replace('\n',''))
        return captcha
