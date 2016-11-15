import pytest
from pathlib import Path
from unittest.mock import Mock, patch, call

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel
from math import sqrt, isclose

import pyqt_test_utils
from pyqt_test_utils import check_widget_snapshot, ImgDiffer


def non_existent_path(name: str):
    path = Path(name)
    if path.exists():
        path.unlink()
    assert not path.exists()
    return path


class TestCaseChecker:
    def setup_class(self):
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

    def test1_gen_first_image(self):
        ref_image_path = non_existent_path('test1_gen_first_image.png')

        files_before = set(Path(__file__).parent.glob('*'))
        widget = QLabel('test')
        check_widget_snapshot(widget, __file__, str(ref_image_path))

        assert ref_image_path.exists()
        files_after = set(Path(__file__).parent.glob('*'))
        assert files_after.difference(files_before) == set([ref_image_path.resolve()])

        ref_image_path.unlink()

    def test_log_and_ref_folder_instead_of_file(self):
        ref_image_path = non_existent_path('test_ref_folder_instead_of_file.png')

        folder = Path(__file__).parent
        files_before = set(folder.glob('*'))
        widget = QLabel('test')
        log = Mock()
        check_widget_snapshot(widget, str(folder), str(ref_image_path), log=log)

        assert ref_image_path.exists()
        assert log.info.call_args == call('Generating ref snapshot %s in %s for widget %s',
                                          'test_ref_folder_instead_of_file.png',
                                          folder, widget)
        files_after = set(folder.glob('*'))
        assert files_after.difference(files_before) == set([ref_image_path.resolve()])
        assert files_after.issuperset(files_before)

        ref_image_path.unlink()

    def test2_old_results(self):
        ref_image_path = non_existent_path('test2_old_results.png')

        # create two bogus files that pretend to be previous results:
        actual_img_path = Path('test2_old_results_actual.png')
        actual_img_path.write_text('')
        diff_img_path = Path('test2_old_results_diff.png')
        diff_img_path.write_text('')
        assert actual_img_path.exists()
        assert diff_img_path.exists()

        # check widget snapshot, with delete-old = False, verify results files still there:
        files_before = set(Path(__file__).parent.glob('*'))
        widget = QLabel('test')
        assert check_widget_snapshot(widget, __file__, 'test2_old_results', delete_old_results=False)
        ref_image_path.unlink()
        assert actual_img_path.exists()
        assert diff_img_path.exists()
        files_after = set(Path(__file__).parent.glob('*'))
        assert files_after == files_before

        # check it again, this time results removed:
        actual_img_path_str = actual_img_path.resolve()
        diff_img_path_str = diff_img_path.resolve()
        assert check_widget_snapshot(widget, __file__, 'test2_old_results')
        ref_image_path.unlink()
        assert not actual_img_path.exists()
        assert not diff_img_path.exists()
        files_after = set(Path(__file__).parent.glob('*'))
        assert files_before.difference(files_after) == set([actual_img_path_str, diff_img_path_str])
        assert files_before.issuperset(files_before)

    def test_equal_images(self):
        ref_image_path = non_existent_path('test_equal_images.png')

        # generate reference:
        files_before = set(Path(__file__).parent.glob('*'))
        widget = QLabel('test')
        assert check_widget_snapshot(widget, __file__, 'test_equal_images')

        # re-check: should find images are identical:
        assert check_widget_snapshot(widget, __file__, 'test_equal_images')
        assert check_widget_snapshot(widget, __file__, 'test_equal_images')
        ref_image_path.unlink()
        files_after = set(Path(__file__).parent.glob('*'))
        assert files_before == files_after

    def test_unequal_images_diff_less_than_tol(self):
        ref_image_path = non_existent_path('test_unequal_images_diff_less_than_tol.png')

        class ImgDiffer_SameWithinTol:
            def get_diff(self, image, ref_image):
                return None

            def report(self):
                return "report"

        # generate reference:
        files_before = set(Path(__file__).parent.glob('*'))
        widget = QLabel('test')
        assert check_widget_snapshot(widget, __file__, 'test_unequal_images_diff_less_than_tol')

        # pretend label has changed, but less than tolerance (get_diff() returns None):
        widget = QLabel('test2')
        widget.setObjectName('label')
        mock_log = Mock()
        assert check_widget_snapshot(widget, __file__, 'test_unequal_images_diff_less_than_tol',
                                     img_differ=ImgDiffer_SameWithinTol(), log=mock_log)
        ref_image_path.unlink()
        assert mock_log.method_calls == [
            call.info('Widget %s vs ref %s in %s:',
                      'label', 'test_unequal_images_diff_less_than_tol.png', ref_image_path.parent.resolve()),
            call.info('    report')
        ]
        # confirm that no results files were created:
        files_after = set(Path(__file__).parent.glob('*'))
        assert files_after == files_before

    def test_unequal_images(self):
        ref_image_path = non_existent_path('test_unequal_images.png')

        class ImgDiffer:
            def get_diff(self, image, ref_image):
                return QImage(image)

            def report(self):
                return "report"

        # generate reference:
        widget = QLabel('test')
        assert check_widget_snapshot(widget, __file__, 'test_unequal_images')

        # pretend label has changed, but less than tolerance (get_diff() returns None):
        widget = QLabel('test2')
        widget.setObjectName('label')
        mock_log = Mock()
        files_before = set(Path(__file__).parent.glob('*'))
        assert not check_widget_snapshot(widget, __file__, 'test_unequal_images',
                                         img_differ=ImgDiffer(), log=mock_log)
        assert mock_log.method_calls == [
            call.info('Widget %s vs ref %s in %s:', 'label', 'test_unequal_images.png',
                      ref_image_path.parent.resolve()),
            call.info('    report'),
            call.warn('    Snapshot has changed beyond tolerances, saving actual and diff images to folder %s:',
                      ref_image_path.parent.resolve()),
            call.warn('    Saving actual image to %s', 'test_unequal_images_actual.png'),
            call.warn('    Saving diff image (White - |ref - widget|) to %s', 'test_unequal_images_diff.png')
        ]
        # confirm that no results files were create:
        files_after = set(Path(__file__).parent.glob('*'))
        ref_image_path.unlink()
        assert files_after.issuperset(files_before)
        actual_img_path = Path('test_unequal_images_actual.png')
        diff_img_path = Path('test_unequal_images_diff.png')
        assert files_after.difference(files_before) == set([actual_img_path.resolve(), diff_img_path.resolve()])
        actual_img_path.unlink()
        diff_img_path.unlink()

    def test_custom_differ(self):
        ref_image_path = non_existent_path('test_custom_differ.png')

        # generate reference:
        widget = QLabel('test')
        assert check_widget_snapshot(widget, __file__, 'test_custom_differ')

        # pretend label has changed, but less than tolerance (get_diff() returns None):
        widget = QLabel('test2')
        widget.setObjectName('label')

        # first check that kwargs when custom differ given causes exception:
        img_differ = Mock()
        img_differ.get_diff.return_value=None
        pytest.raises(ValueError,
                      check_widget_snapshot, widget, __file__, 'test_custom_differ',
                      img_differ=img_differ, kwarg1=1, kwarg2=2)
        assert check_widget_snapshot(widget, __file__, 'test_custom_differ', img_differ=img_differ)
        assert len(img_differ.method_calls) == 1
        assert img_differ.get_diff.call_count == 1

        img_differ_class = Mock()
        img_differ_class.return_value.get_diff.return_value=None
        with patch.object(pyqt_test_utils, 'ImgDiffer', img_differ_class) as mock_default_differ:
            assert check_widget_snapshot(widget, __file__, 'test_custom_differ')
            assert mock_default_differ.call_args_list == [call()]

        ref_image_path.unlink()


class TestCaseImgDiffer:

    @pytest.fixture(autouse=True)
    def setup_class(self):
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

    def test_same_img(self):
        widget1 = QLabel('test1')
        widget2 = QLabel('test1')
        ref_img = widget1.grab().toImage()
        img = widget2.grab().toImage()
        assert img == ref_img

        differ = ImgDiffer()
        assert differ.get_diff(img, ref_img) is None
        assert differ.report() == "RMS diff=0.00% (rms_tol_perc=0.00%), number of pixels changed=0.00% (num_tol_perc=None)"

    def test_actual_wider(self):
        widget_ref = QLabel('test1')
        widget_actual = QLabel('test23456')

        def test():
            widget_ref.show()
            widget_actual.show()

            ref_img = widget_ref.grab().toImage()
            img = widget_actual.grab().toImage()
            assert img != ref_img
            assert img.width() > ref_img.width()
            assert img.height() == ref_img.height()

            differ = ImgDiffer()
            diff = differ.get_diff(img, ref_img)
            # diff.save('actual_wider_diff.png')
            expect = QPixmap('actual_wider_diff.png')
            assert expect.toImage() == diff

            self.app.closeAllWindows()

        QTimer.singleShot(0, test)
        self.app.exec()

    def test_actual_higher(self):
        widget1 = QLabel('test1')
        widget2 = QLabel('test1\n123')

        def test():
            widget1.show()
            widget2.show()

            ref_img = widget1.grab().toImage()
            img = widget2.grab().toImage()
            assert img != ref_img
            assert img.width() == ref_img.width()
            assert img.height() != ref_img.height()

            differ = ImgDiffer()
            diff = differ.get_diff(img, ref_img)
            # diff.save('actual_higher_diff.png')
            expect = QPixmap('actual_higher_diff.png')
            assert expect.toImage() == diff

            self.app.closeAllWindows()

        QTimer.singleShot(0, test)
        self.app.exec()

    def test_same_size_img_not_eq(self):
        widget_ref = QLabel('test1')
        widget_actual = QLabel('test2')

        def test():
            widget_actual.show()
            widget_ref.setFixedSize(widget_actual.width(), widget_actual.height())
            widget_ref.show()

            ref_img = widget_ref.grab().toImage()
            img = widget_actual.grab().toImage()
            assert img != ref_img
            assert img.size() == ref_img.size()

            differ = ImgDiffer()
            diff = differ.get_diff(img, ref_img)
            # diff.save('same_size_img_neq.png')
            expect = QPixmap('same_size_img_neq.png')
            assert expect.toImage() == diff
            report = differ.report()
            assert report == "RMS diff=37.22% (rms_tol_perc=0.00%), number of pixels changed=10.46% (num_tol_perc=None)"

            self.app.closeAllWindows()

        QTimer.singleShot(0, test)
        self.app.exec()

    def create_same_size_images(self, width: int, height: int, color: QColor) -> (QImage, QImage, QImage):
        IMG_FORMAT = QImage.Format_ARGB32

        # create ref
        ref_img = QImage(width, height, IMG_FORMAT)
        for i in range(ref_img.width()):
            for j in range(ref_img.height()):
                ref_img.setPixelColor(i, j, color)

        # create actual = ref:
        actual_img = ref_img.copy()
        assert actual_img is not ref_img
        assert actual_img == ref_img

        # create blank diff
        diff_img = QImage(width, height, IMG_FORMAT)
        for i in range(diff_img.width()):
            for j in range(diff_img.height()):
                diff_img.setPixelColor(i, j, QColor('black'))

        return ref_img, actual_img, diff_img

    def test_same_size_one_pixel_diff(self):
        ref_img, actual_img, expect_diff_img = self.create_same_size_images(101, 102, QColor(103, 104, 105, 106))
        actual_img.setPixelColor(50, 50, QColor(0, 0, 0, 0))
        expect_diff_img.setPixelColor(50, 50, QColor(103, 104, 105, 106))

        differ = ImgDiffer()
        diff_img = differ.get_diff(actual_img, ref_img)
        assert expect_diff_img == diff_img
        assert differ.num_diffs_perc == 1/(101*102)*100
        assert differ.max_pix_diff == 106
        assert differ.diff_rms_perc == 100 * sqrt(pow(103, 2) + pow(104, 2) + pow(105, 2) + pow(106, 2)) / 2 / 255
        report = differ.report()
        assert report == "RMS diff=40.98% (rms_tol_perc=0.00%), number of pixels changed=0.01% (num_tol_perc=None)"

        # various cases that should produce no diff:
        assert ImgDiffer(rms_tol_perc=42).get_diff(actual_img, ref_img) is None
        assert ImgDiffer(num_tol_perc=0.01).get_diff(actual_img, ref_img) is None
        assert ImgDiffer(max_pix_diff_tol=110).get_diff(actual_img, ref_img) is None
        assert ImgDiffer(rms_tol_perc=42, num_tol_perc=0.01, max_pix_diff_tol=110).get_diff(actual_img, ref_img) is None

        # various cases that should produce same diff:
        assert ImgDiffer(rms_tol_perc=40).get_diff(actual_img, ref_img) == expect_diff_img
        assert ImgDiffer(num_tol_perc=0.001).get_diff(actual_img, ref_img) == expect_diff_img
        assert ImgDiffer(max_pix_diff_tol=100).get_diff(actual_img, ref_img) == expect_diff_img

    def test_same_size_all_pixel_diff(self):
        ref_img, actual_img, expect_diff_img = self.create_same_size_images(101, 102, QColor(103, 104, 105, 106))
        for i in range(ref_img.width()):
            for j in range(ref_img.height()):
                pixel_color = ref_img.pixelColor(i, j)
                actual_img.setPixelColor(i, j, QColor(*[c+2 for c in pixel_color.getRgb()]))
                expect_diff_img.setPixelColor(i, j, QColor(2, 2, 2, 2))

        differ = ImgDiffer()
        diff_img = differ.get_diff(actual_img, ref_img)
        assert expect_diff_img == diff_img
        assert differ.num_diffs_perc == 100
        assert differ.max_pix_diff == 2
        assert isclose(differ.diff_rms_perc, 100 * 2 / 255)
        report = differ.report()
        assert report == "RMS diff=0.78% (rms_tol_perc=0.00%), number of pixels changed=100.00% (num_tol_perc=None)"

        # various cases that should produce no diff:
        assert ImgDiffer(rms_tol_perc=1).get_diff(actual_img, ref_img) is None
        assert ImgDiffer(max_pix_diff_tol=2).get_diff(actual_img, ref_img) is None
        assert ImgDiffer(rms_tol_perc=1, max_pix_diff_tol=2).get_diff(actual_img, ref_img) is None

        # various cases that should produce same diff:
        assert ImgDiffer(rms_tol_perc=1/3).get_diff(actual_img, ref_img) == expect_diff_img
        assert ImgDiffer(max_pix_diff_tol=1).get_diff(actual_img, ref_img) == expect_diff_img
