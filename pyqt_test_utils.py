# Use, distribution and modification of this file is bound by the terms of the MIT (expat) license. 

"""
Various testing utilities for PyQt. 
"""

__author__ = "Oliver Schoenborn"
__license__ = "MIT"
__version__ = '0.9.0'

from pathlib import Path
from math import sqrt

from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QImage, QPixmap, QColor

__all__ = ['check_widget_snapshot']


class ImgDiffer:

    def __init__(self, rms_tol_perc: float = 0.0, num_tol_perc: float = 0.0, max_pix_diff_tol: int = 0):
        """
        :param rms_tol_perc: percentage difference allowed between widget's snapshot and the reference, i.e.
            a floating point value in range 0..100
        :param num_tol_perc: the maximum percentage of mismatched pixels allowed, relative to total number
            of pixels in the reference image; two pixels differ if any of their R, G, B and A values differ
        """
        self.rms_tol_perc = float(rms_tol_perc)  # ensure FPV so report can format
        self.num_tol_perc = float(num_tol_perc)  # ensure FPV so report can format
        self.max_pix_diff_tol = max_pix_diff_tol

        self.diff_rms_perc = None
        self.num_diffs_perc = None

    def get_diff(self, image: QImage, ref_image: QImage) -> QImage:
        diff_width = max(ref_image.width(), image.width())
        diff_height = max(ref_image.height(), image.height())
        diff_image = QImage(diff_width, diff_height, ref_image.format())

        diff_rms = 0
        num_diffs = 0
        max_pix_diff = 0
        total_num_pixels = 0
        for i in range(diff_width):
            for j in range(diff_height):
                pixel = image.pixelColor(i, j)
                ref_pixel = ref_image.pixelColor(i, j)
                if pixel.isValid() and ref_pixel.isValid():
                    total_num_pixels += 1
                    if pixel == ref_pixel:
                        diff_image.setPixelColor(i, j, self._get_pixel_diff_ref_color())
                    else:
                        num_diffs += 1
                        diff_rms_pix, diff_color = self._get_pixel_diff(pixel, ref_pixel)
                        diff_rms += diff_rms_pix
                        max_diff = max(diff_color)
                        if max_diff > max_pix_diff:
                            max_pix_diff = max_diff
                        diff_image.setPixelColor(i, j, QColor(*diff_color))

                elif pixel.isValid():
                    diff_image.setPixelColor(i, j, pixel)

                elif ref_pixel.isValid():
                    diff_image.setPixelColor(i, j, ref_pixel)

                else:
                    COLOR_NO_PIXEL = QColor(0, 0, 0)
                    diff_image.setPixelColor(i, j, COLOR_NO_PIXEL)

        if num_diffs == 0:
            return None

        diff_rms /= num_diffs
        self.diff_rms_perc = diff_rms * 100
        self.num_diffs_perc = (num_diffs / total_num_pixels) * 100

        diff_acceptable = (self.diff_rms_perc <= self.rms_tol_perc and
                           self.num_diffs_perc <= self.num_tol_perc and
                           max_pix_diff <= self.max_pix_diff_tol)
        return None if diff_acceptable else diff_image

    def report(self) -> str:
        return "RMS diff={:.2}% (rms_tol_perc={:.2}%), # pixels changed={:.2}% (num_tol_perc={:.2}%)".format(
            self.diff_rms_perc, self.rms_tol_perc, self.num_diffs_perc, self.num_tol_perc)

    def _get_pixel_diff(self, pix_color: QColor, ref_pix_color: QColor) -> (int, int, int, int):
        DIFF_MAX = 255
        DIFF_REF_PIX = self._get_pixel_diff_ref()
        pix_rgba = pix_color.getRgb()
        ref_pix_rgba = ref_pix_color.getRgb()
        diff = [pow((x - y) / DIFF_MAX, 2) for x, y in zip(pix_rgba, ref_pix_rgba)]
        diff_rms = sqrt(sum(diff) / len(pix_rgba))
        diff_color = [DIFF_REF_PIX - abs(x - y) for x, y in zip(pix_rgba, ref_pix_rgba)]
        return diff_rms, diff_color

    def _get_pixel_diff_ref_color(self) -> (int, int, int):
        DIFF_REF_PIX = self._get_pixel_diff_ref()
        return QColor(DIFF_REF_PIX, DIFF_REF_PIX, DIFF_REF_PIX)

    def _get_pixel_diff_ref(self) -> int:
        DIFF_REF_PIX = 255  # value corresponds to "no difference"
        return DIFF_REF_PIX


# Discussion of check_widget_snapshot() is at
# http://www.codeproject.com/Tips/1134902/Testing-QWidget-Snapshot-Regression-in-PyQt.
def check_widget_snapshot(widget: QWidget, ref_path: str, fig_name: str, delete_old_results: bool = True,
                          img_differ: ImgDiffer = None, log=None, **img_diff_kwargs) -> bool:
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

    :return: True if reference didn't exist (and was hence generated); True if widget matches reference;
        True if not matched but RMS diff is less than rms_tol_perc % and number of different pixels
        &lt; max_num_diffs; False otherwise

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
    actual_pixmap = widget.grab()
    image = actual_pixmap.toImage()

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
        actual_pixmap.save(str(ref_pixmap_path))
        return True

    # it exists, so compare to it, return if identical:
    ref_pixmap = QPixmap(str(ref_pixmap_path))
    ref_image = ref_pixmap.toImage()
    if ref_image == image:
        return True

    # not equal so get a diff image if diff is too large:
    if img_differ is None:
        img_differ = ImgDiffer(**img_diff_kwargs)
    else:
        if img_diff_kwargs:
            msg = "Unknown kwargs {} (because img_differ was given rather than None)"
            raise ValueError(msg.format(img_diff_kwargs))

    diff_image = img_differ.get_diff(image, ref_image)
    if log is not None:
        log.info("Widget %s vs ref %s in %s:",
                 widget.objectName() or repr(widget), ref_pixmap_path.name, ref_pixmap_path.parent)
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
