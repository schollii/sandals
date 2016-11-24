# Use, distribution and modification of this file is bound by the terms of the MIT (expat) license. 

"""
Various testing utilities for PyQt. 
"""

import re
from pathlib import Path
from math import sqrt
from time import perf_counter, sleep

from PyQt5.QtWidgets import QWidget, qApp
from PyQt5.QtGui import QImage, QPixmap, QColor

__all__ = ['check_widget_snapshot', 'ImgDiffer']

__author__ = "Oliver Schoenborn"
__license__ = "MIT"
__version__ = '0.9.0'


class ImgDiffer:
    """
    Default class used by check_widget_snapshot in order to measure whether two images are sufficiently 
    similar to be considered as identical. The images are assumed to come from QWidget.grab(), so the 
    differences measured are simple: 
    
    - if two images are identical, get_img_diff(image1, image2) returns None
    - if the two images differ beyond specified tolerances, get_img_diff(image1, image2) returns a QImage 
      instance that contains the differences between the two images. Each pixel that is the same in both 
      images is black in the diff image, and each pixel that is different is the absolute difference between 
      the two pixels. So a pixel that is black in image1 and white in image2, or vice versa, will show up 
      as a white pixel in the diff image. 
      
    This class computes the RMS difference between pixels averaged over the number of different pixels, 
    the percentage of pixels that are different, and the largest difference between two channels. 
    The following situations are covered: 
    
    - images where most pixels differ by a small amount, and other pixels are identical: large percentage 
      of pixels are different, but by a small RMS amount
    - images where very few pixels differ, but they differ by a lot: small percentage of pixels are different,
      but by a large RMS amount
    - a mixture of the two: RMS could be small if lots of pixels changed by a small amount and a few pixels 
      changed by a large amount (for example, if a label changed text, like an "i" for an "l"), but max change 
      will be large.
      
    If a diff is executed on the same platform all the time, the differ should probably have 0 tolerance 
    (any change is likely a regression). But if a diff is executed on several machines, small differences 
    could be visible due to anti-aliasing effects so they do not represent a true difference. In this case
    the 3 tolerances should be non-zero but small. 
    """

    DIFF_REF_COLOR = 0
    PIXEL_COLOR_NO_DIFF = QColor(DIFF_REF_COLOR, DIFF_REF_COLOR, DIFF_REF_COLOR, DIFF_REF_COLOR)
    PIXEL_COLOR_NO_PIXEL = QColor('white')

    def __init__(self, rms_tol_perc: float = None, num_tol_perc: float = None, max_pix_diff_tol: int = None):
        """
        :param rms_tol_perc: percentage difference allowed between images, i.e. a floating point value in range 
            0..100. 
        :param num_tol_perc: the maximum percentage of mismatched pixels allowed, relative to total number
            of pixels in the reference image. I.e. a floating point value in range 0..100. Two pixels differ 
            if any of their R, G, B and A values differ. 
        :param max_pix_diff_tol: maximum difference allowed in any one pixel, i.e. an integer in the range 
            0..255.

        At least one of the three must be non-None. If all 3 are None, rms_tol_perc will be set to zero,
        implying strict equality only (no differences allowed).
        
        A value of 0 for any of the parameters means the images must be strictly identical otherwise a diff 
        will be produced.
        
        For any of the parameters, a value equal to the maximum is that same as setting the value to None:
        that parameter is not used to determine whether a difference image should be returned. 
        """
        if rms_tol_perc is None and num_tol_perc is None and max_pix_diff_tol is None:
            rms_tol_perc = 0.0
        self.rms_tol_perc = None if rms_tol_perc is None else float(rms_tol_perc)  # ensure FPV so report can format
        self.num_tol_perc = None if num_tol_perc is None else float(num_tol_perc)  # ensure FPV so report can format
        self.max_pix_diff_tol = max_pix_diff_tol

        self.diff_rms_perc = None
        self.num_diffs_perc = None
        self.max_pix_diff = None

    def get_diff(self, image: QImage, ref_image: QImage) -> QImage:
        """
        Get a difference image that represents the differences between two images. 
        Identical pixels produce a black pixel, otherwise the pixel is the absolute 
        difference of the two colors. If the images are different sizes, a diff 
        image will be returned regardless of the tolerances specified at construction
        time. In that case, the areas that do not overlap will have the pixels from 
        the image that has pixels in those areas. In an area where neither image 
        has pixels (because they have different widths AND heights), the color will
        be white. 
        """
        diff_width = max(ref_image.width(), image.width())
        diff_height = max(ref_image.height(), image.height())
        diff_image = QImage(diff_width, diff_height, ref_image.format())

        diff_rms = 0
        num_diffs = 0
        self.max_pix_diff = 0
        total_num_pixels = 0
        
        for i in range(diff_width):
            for j in range(diff_height):
                actual_valid_coord = image.valid(i, j)
                ref_valid_coord = ref_image.valid(i, j)

                if actual_valid_coord and ref_valid_coord:
                    pixel = image.pixelColor(i, j)
                    ref_pixel = ref_image.pixelColor(i, j)

                    total_num_pixels += 1
                    if pixel == ref_pixel:
                        diff_image.setPixelColor(i, j, self.PIXEL_COLOR_NO_DIFF)
                    else:
                        num_diffs += 1
                        diff_rms_pix, diff_color = self._get_pixel_diff(pixel, ref_pixel)
                        diff_rms += diff_rms_pix
                        max_diff = max(diff_color)
                        if max_diff > self.max_pix_diff:
                            self.max_pix_diff = max_diff
                        diff_image.setPixelColor(i, j, QColor(*diff_color))

                elif actual_valid_coord:
                    pixel = image.pixelColor(i, j)
                    diff_image.setPixelColor(i, j, pixel)

                elif ref_valid_coord:
                    ref_pixel = ref_image.pixelColor(i, j)
                    diff_image.setPixelColor(i, j, ref_pixel)

                else:
                    diff_image.setPixelColor(i, j, self.PIXEL_COLOR_NO_PIXEL)

        self.num_diffs_perc = (num_diffs / total_num_pixels) * 100
        if num_diffs == 0:
            self.diff_rms_perc = 0.0
            if ref_image.width() == image.width() and ref_image.height() == image.height():
                return None
            return diff_image

        else:
            diff_rms /= num_diffs
            self.diff_rms_perc = diff_rms * 100

            rms_ok = (self.rms_tol_perc is None or self.diff_rms_perc <= self.rms_tol_perc)
            num_diff_ok = (self.num_tol_perc is None or self.num_diffs_perc <= self.num_tol_perc)
            max_pix_diff_ok = (self.max_pix_diff_tol is None or self.max_pix_diff <= self.max_pix_diff_tol)
            diff_acceptable = (rms_ok and num_diff_ok and max_pix_diff_ok)
            return None if diff_acceptable else diff_image

    def report(self) -> str:
        """
        Returns a text string that describes the actual difference metrics computed by the last 
        get_diff(), as well as the tolerances that were used. 
        """
        msg = "RMS diff={%} (rms_tol_perc={%}), number of pixels changed={%} (num_tol_perc={%}), max pix diff={} (max_pix_diff_tol={})"
        msg = re.sub('\{%\}', '{:.2f}%', msg)
        results = (self.diff_rms_perc, self.rms_tol_perc, self.num_diffs_perc, self.num_tol_perc, self.max_pix_diff, self.max_pix_diff_tol)
        return msg.format(*results)

    def _get_pixel_diff(self, pix_color: QColor, ref_pix_color: QColor) -> (float, (int, int, int, int)):
        """
        Get the difference between two pixels. The returns a pair: first item is the RMS of the 
        differences across all 4 channels of the colors (RGBA); second item is the absolute 
        difference between the pixel channels. 
        """
        DIFF_MAX = 255
        pix_rgba = pix_color.getRgb()
        ref_pix_rgba = ref_pix_color.getRgb()

        diff = [pow((x - y) / DIFF_MAX, 2) for x, y in zip(pix_rgba, ref_pix_rgba)]
        diff_rms = sqrt(sum(diff) / len(pix_rgba))

        diff_color = [abs(x - y) for x, y in zip(pix_rgba, ref_pix_rgba)]

        return diff_rms, diff_color


# Discussion of check_widget_snapshot() is at
# http://www.codeproject.com/Tips/1134902/Testing-QWidget-Snapshot-Regression-in-PyQt.
def check_widget_snapshot(widget: QWidget, ref_path: str, fig_name: str, delete_old_results: bool = True,
                          img_differ: ImgDiffer = None, log=None, try_sec: float=None, try_interval: float=0.01, 
                          **img_diff_kwargs) -> bool:
    """
    Get the difference between a widget's appearance and a file stored on disk. If the file doesn't
    exist, the file is created.
    
    :param widget: the widget for which appearance must be verified
    :param ref_path: the path to folder containing reference image (can be a file name too, then the
        parent is used as folder -- useful for tests where __file__ can be passed)
    :param fig_name: the name of the reference image (will be saved in ref_path folder if it doesn't
        exist, or read if it does)
    :param delete_old_results: if True, any previous image results will be deleted (default); else keep them
        even if the check passes (could be misleading)
    :param img_differ: instance that adheres ot ImgDiffer protocol; default created if None
    :param log: a logging.Logger instance 
    :param try_sec: If this is None, only one comparison is made between the widgets. Otherwise, the 
        comparison is made repeatedly every try_interval seconds, until at least try_sec seconds have elapsed. 
    :param try_interval: seconds to wait between tries. Must be < try_sec. 

    :return: True if reference didn't exist (and was hence generated); True if widget matches reference;
        True if not matched but tolerances were sufficiently large to treat as identical; False otherwise.

    Example use:

        # file some_test.py in folder 'testing'
        app = QApplication([])
        widget = QLabel('test')
        assert check_widget_snapshot(widget, __file__, 'label', rms_tol_perc=0.5, num_tol_perc=4)

    The first time the test is run, it will save a snapshot of the widget to label.png in 
    Path(__file__).parent and return True. The next time it is run, the widget snapshot will be compared 
    to the image saved. If the image colors have changed by more than 0.5% when averaged over all pixels, 
    or if more than 4% of pixels have changed in any way, check_widget_snapshot() will save a snapshot 
    of the widget to label_actual.png and the difference image to label_diff.png and will return False, 
    thus causing the test to fail. Otherwise (no differences, or differences within stated bounds), 
    check_widget_snapshot() will just return True and the test will pass.
    """
    ref_path = Path(ref_path)
    if ref_path.is_file():
        ref_path = ref_path.parent
    assert ref_path.is_dir()
    ref_pixmap_path = (ref_path / fig_name).with_suffix('.png')
    actual_pix_path = ref_pixmap_path.with_name(fig_name + '_actual.png')
    diff_pix_path = ref_pixmap_path.with_name(fig_name + '_diff.png')
    assert actual_pix_path.parent == diff_pix_path.parent

    # delete any old data:
    if delete_old_results:
        if actual_pix_path.exists():
            actual_pix_path.unlink()
        if diff_pix_path.exists():
            diff_pix_path.unlink()

    # if ref image doesn't exist, generate it and return:
    if not ref_pixmap_path.exists():
        if log is not None:
            log.info('Generating ref snapshot %s in %s for widget %s',
                     ref_pixmap_path.name, ref_pixmap_path.parent, widget)
        actual_pixmap = widget.grab()
        actual_pixmap.save(str(ref_pixmap_path))
        return True

    # it exists, so compare to it, return if identical:
    ref_pixmap = QPixmap(str(ref_pixmap_path))
    ref_image = ref_pixmap.toImage()
    actual_pixmap = widget.grab()
    image = actual_pixmap.toImage()

    if try_sec is not None:
        start_time = perf_counter()
        while ref_image != image and perf_counter() - start_time < try_sec:
            qApp.processEvents()
            sleep(try_interval)
            actual_pixmap = widget.grab()
            image = actual_pixmap.toImage()

    if ref_image == image:
        return True

    # not equal so get a diff image if diff is too large:
    start_time = perf_counter()
    if img_differ is None:
        img_differ = ImgDiffer(**img_diff_kwargs)
    else:
        if img_diff_kwargs:
            msg = "Unknown kwargs {} (because img_differ was given rather than None)"
            raise ValueError(msg.format(img_diff_kwargs))

    diff_image = img_differ.get_diff(image, ref_image)        
    time_required = perf_counter() - start_time

    if log is not None:
        log.info("Widget %s vs ref %s in %s (%.2f sec):",
                 widget.objectName() or repr(widget), ref_pixmap_path.name, ref_pixmap_path.parent, time_required)
        log.info(" " * 4 + img_differ.report())
            
    if diff_image is None:
        return True
            
    # save the actual and diff image
    if log is not None:
        log.warn("    Snapshot has changed beyond tolerances, saving actual and diff images to folder %s:",
                 actual_pix_path.parent)
        log.warn("    Saving actual image to %s", actual_pix_path.name)
        log.warn("    Saving diff image (White - |ref - widget|) to %s", diff_pix_path.name)

    actual_pixmap.save(str(actual_pix_path))
    diff_pixmap = QPixmap(diff_image)
    diff_pixmap.save(str(diff_pix_path))

    return False
