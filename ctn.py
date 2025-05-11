import sys
import time
import math
import multiprocessing
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QSplitter, QVBoxLayout,
                             QHBoxLayout, QPushButton, QProgressBar, QPlainTextEdit,
                             QLabel, QFileDialog, QAction, QDialog, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import psutil
import cpuinfo

def compute(_=None):
    """CPU密集型计算任务"""
    result = 0
    for i in range(3000000):
        result += math.sqrt(i) * math.exp(math.sin(math.radians(i)))
    return result

class Worker(QThread):
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    result_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.single_times = []
        self.multi_times = []

    def run(self):
        try:
            for i in range(3):
                if not self.running:
                    break
                
                # 单核测试
                self.update_signal.emit(f"第{i+1}轮单核测试开始...")
                start_time = time.time()
                compute()
                elapsed = time.time() - start_time
                self.single_times.append(elapsed)
                self.progress_signal.emit((i * 2) + 1)
                self.update_signal.emit(f"第{i+1}轮单核测试完成 耗时: {elapsed:.2f}秒\n")

                if not self.running:
                    break
                
                # 多核测试
                self.update_signal.emit(f"第{i+1}轮多核测试开始...")
                start_time = time.time()
                processes = multiprocessing.cpu_count()
                with multiprocessing.Pool(processes) as pool:
                    pool.map(compute, range(processes))
                elapsed = time.time() - start_time
                self.multi_times.append(elapsed)
                self.progress_signal.emit((i * 2) + 2)
                self.update_signal.emit(f"第{i+1}轮多核测试完成 耗时: {elapsed:.2f}秒\n")

            if self.running and len(self.single_times) == 3:
                avg_single = sum(self.single_times) / 3
                avg_multi = sum(self.multi_times) / 3
                score_single = 10000 / (avg_single + 0.1)
                score_multi = 10000 / (avg_multi + 0.1)
                self.result_signal.emit({
                    'single_time': avg_single,
                    'multi_time': avg_multi,
                    'single_score': score_single,
                    'multi_score': score_multi
                })

        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            self.update_signal.emit("测试完成")

    def stop(self):
        self.running = False

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setFixedSize(300, 200)
        layout = QVBoxLayout()
        text = QLabel("CPU性能测试工具\n\n版本: 1.0\n作者: HelloWorld05\n"
                     "本工具用于测试CPU的单核和多核性能")
        layout.addWidget(text)
        self.setLayout(layout)

class ReferenceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("参考分数")
        self.setFixedSize(400, 300)
        layout = QVBoxLayout()
        text = QLabel(
            "参考分数（示例）:\n\n"
            "AMD Ryzen 7 8845HS: 单核21700 | 多核7700\n"
            "Apple M2 Max: 单核8200 | 多核28500\n\n"
            "分数越高表示性能越好"
        )
        layout.addWidget(text)
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CPU性能测试工具")
        self.setGeometry(100, 100, 800, 600)
        self.worker = None
        self.test_results = {}
        self.init_ui()
        self.load_cpu_info()

    def init_ui(self):
        # 主分割布局
        splitter = QSplitter(Qt.Horizontal)

        # 左侧CPU信息面板
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        self.cpu_labels = {
            'name': QLabel(),
            'cores': QLabel(),
            'threads': QLabel(),
            'freq': QLabel()
        }
        for label in self.cpu_labels.values():
            left_layout.addWidget(label)
        left_panel.setLayout(left_layout)

        # 右侧控制面板
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始测试")
        self.stop_btn = QPushButton("终止测试")
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setMaximum(6)
        
        # 日志输出
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        
        # 保存按钮
        self.save_btn = QPushButton("保存结果")
        
        right_layout.addLayout(btn_layout)
        right_layout.addWidget(self.progress)
        right_layout.addWidget(self.log)
        right_layout.addWidget(self.save_btn)
        right_panel.setLayout(right_layout)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        self.setCentralWidget(splitter)

        # 菜单栏
        menubar = self.menuBar()
        help_menu = menubar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        reference_action = QAction("参考分数", self)
        reference_action.triggered.connect(self.show_reference)
        help_menu.addAction(about_action)
        help_menu.addAction(reference_action)

        # 信号连接
        self.start_btn.clicked.connect(self.start_test)
        self.stop_btn.clicked.connect(self.stop_test)
        self.save_btn.clicked.connect(self.save_results)

    def load_cpu_info(self):
        try:
            info = cpuinfo.get_cpu_info()
            cpu_freq = psutil.cpu_freq()
            self.cpu_labels['name'].setText(f"型号: {info['brand_raw']}")
            self.cpu_labels['cores'].setText(f"物理核心: {psutil.cpu_count(logical=False)}")
            self.cpu_labels['threads'].setText(f"逻辑核心: {psutil.cpu_count(logical=True)}")
            self.cpu_labels['freq'].setText(f"当前频率: {cpu_freq.current:.0f}MHz" if cpu_freq else "频率: 未知")
        except Exception as e:
            QMessageBox.warning(self, "警告", f"无法获取CPU信息: {str(e)}")

    def start_test(self):
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log.clear()
        self.progress.setValue(0)
        self.test_results.clear()
        
        self.worker = Worker()
        self.worker.update_signal.connect(self.update_log)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.result_signal.connect(self.show_results)
        self.worker.error_signal.connect(self.show_error)
        self.worker.finished.connect(self.test_completed)
        self.worker.start()

    def stop_test(self):
        if self.worker:
            self.worker.stop()
            self.worker.terminate()
            self.test_completed()
            self.log.appendPlainText("测试已终止")

    def update_log(self, message):
        self.log.appendPlainText(message)

    def show_results(self, results):
        self.test_results = results
        self.log.appendPlainText(
            f"\n最终结果:\n"
            f"单核平均耗时: {results['single_time']:.2f}s | 分数: {results['single_score']:.0f}\n"
            f"多核平均耗时: {results['multi_time']:.2f}s | 分数: {results['multi_score']:.0f}"
        )

    def show_error(self, error):
        QMessageBox.critical(self, "错误", f"测试过程中发生错误:\n{error}")

    def test_completed(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.worker = None

    def save_results(self):
        if not self.test_results:
            QMessageBox.warning(self, "警告", "没有可保存的测试结果")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "保存结果", "", "文本文件 (*.txt)")
        if path:
            try:
                with open(path, 'w') as f:
                    f.write(f"CPU信息:\n")
                    f.write(f"{self.cpu_labels['name'].text()}\n")
                    f.write(f"{self.cpu_labels['cores'].text()}\n")
                    f.write(f"{self.cpu_labels['threads'].text()}\n\n")
                    f.write(f"测试结果:\n")
                    f.write(f"单核平均时间: {self.test_results['single_time']:.2f}s\n")
                    f.write(f"单核分数: {self.test_results['single_score']:.0f}\n")
                    f.write(f"多核平均时间: {self.test_results['multi_time']:.2f}s\n")
                    f.write(f"多核分数: {self.test_results['multi_score']:.0f}\n")
                QMessageBox.information(self, "保存成功", "结果已成功保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存文件失败: {str(e)}")

    def show_about(self):
        dialog = AboutDialog(self)
        dialog.exec_()

    def show_reference(self):
        dialog = ReferenceDialog(self)
        dialog.exec_()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())