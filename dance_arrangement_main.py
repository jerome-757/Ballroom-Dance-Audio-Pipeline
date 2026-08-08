import random
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
from collections import Counter
import pandas as pd
import os
import glob
import warnings
warnings.filterwarnings('ignore')

# ---------- 全局数据 ----------
DATA = []
POOL = []
TOTAL = 0

class PlaylistApp:
    def __init__(self, root):
        self.root = root
        root.title("舞曲排布工具-魅影制作")
        
        # ---------- 窗口居中 ----------
        window_width = 1200
        window_height = 650
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        root.minsize(1050, 600)
        
        # ---------- 主布局：左右结构 ----------
        main_frame = tk.Frame(root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # -------- 左侧：控制面板（加宽） --------
        left_frame = tk.Frame(main_frame, width=580)
        left_frame.pack(side="left", fill="both", expand=False, padx=(0, 10))
        left_frame.pack_propagate(False)
        
        # ---------- 数据加载区 ----------
        frame_data = tk.LabelFrame(left_frame, text="数据源", padx=8, pady=5)
        frame_data.pack(fill="x", pady=3)
        
        # 自动查找Excel文件
        default_path = self.find_excel_file()
        self.data_path = tk.StringVar(value=default_path)
        
        path_frame = tk.Frame(frame_data)
        path_frame.pack(fill="x")
        
        # 路径输入框尽量拉长
        self.path_entry = tk.Entry(path_frame, textvariable=self.data_path)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        tk.Button(path_frame, text="加载", command=self.load_data, width=6).pack(side="right")
        tk.Button(path_frame, text="浏览", command=self.browse_file, width=6).pack(side="right", padx=(0, 5))
        
        self.data_status = tk.Label(frame_data, text="未加载", fg="red", font=("Arial", 8))
        self.data_status.pack(anchor="w", pady=2)
        
        # ---------- 固定位置设置区（1行 x 3列 = 3个格子） ----------
        frame_fixed = tk.LabelFrame(left_frame, text="固定位置（位置=舞种，如 2=华尔兹）", padx=8, pady=5)
        frame_fixed.pack(fill="x", pady=3)
        
        self.fixed_positions = {}
        self.fixed_entries = []
        
        row = tk.Frame(frame_fixed)
        row.pack(pady=3, fill="x")
        for col_idx in range(3):
            cell = tk.Frame(row, relief=tk.RIDGE, bd=1, padx=5, pady=3)
            cell.pack(side="left", padx=8, expand=True, fill="x")
            
            pos_entry = tk.Entry(cell, width=4)
            pos_entry.pack(side="left", padx=2)
            tk.Label(cell, text="=", font=("Arial", 9)).pack(side="left")
            dance_entry = tk.Entry(cell, width=14)
            dance_entry.pack(side="left", padx=2, fill="x", expand=True)
            
            self.fixed_entries.append((pos_entry, dance_entry))
        
        btn_frame = tk.Frame(frame_fixed)
        btn_frame.pack(pady=3)
        tk.Button(btn_frame, text="应用固定位置", command=self.apply_fixed_positions, width=14).pack(side="left", padx=2)
        tk.Button(btn_frame, text="清空", command=self.clear_fixed_positions, width=8).pack(side="left", padx=2)
        
        # ---------- 规则勾选区 ----------
        frame_rules = tk.LabelFrame(left_frame, text="规则列表", padx=8, pady=5)
        frame_rules.pack(fill="x", pady=3)
        
        self.rules = {
            '同舞种间隔': tk.BooleanVar(value=True),
            '大类不连续三次': tk.BooleanVar(value=True),
            '节奏约束': tk.BooleanVar(value=True),
        }
        
        self.gap_value = tk.StringVar(value="6")
        
        # 规则1：同舞种间隔
        row1 = tk.Frame(frame_rules)
        row1.pack(fill="x", pady=1)
        cb1 = tk.Checkbutton(row1, variable=self.rules['同舞种间隔'])
        cb1.pack(side="left")
        tk.Label(row1, text="同一舞种至少隔开").pack(side="left")
        gap_entry = tk.Entry(row1, width=4, textvariable=self.gap_value)
        gap_entry.pack(side="left", padx=2)
        tk.Label(row1, text="首（位置差≥N）").pack(side="left")
        
        # 规则2：大类不连续三次
        row2 = tk.Frame(frame_rules)
        row2.pack(fill="x", pady=1)
        cb2 = tk.Checkbutton(row2, variable=self.rules['大类不连续三次'])
        cb2.pack(side="left")
        tk.Label(row2, text="连续3首大类不能相同").pack(side="left")
        
        # 规则3：节奏约束
        row3 = tk.Frame(frame_rules)
        row3.pack(fill="x", pady=1)
        cb3 = tk.Checkbutton(row3, variable=self.rules['节奏约束'])
        cb3.pack(side="left")
        tk.Label(row3, text="中速/慢速不三连，不允许快-快").pack(side="left")
        
        # ---------- 搜索参数 ----------
        frame_params = tk.Frame(left_frame)
        frame_params.pack(fill="x", pady=5)
        
        tk.Label(frame_params, text="搜索次数:").pack(side="left")
        self.max_attempts = tk.StringVar(value="50000")
        tk.Entry(frame_params, width=8, textvariable=self.max_attempts).pack(side="left", padx=5)
        tk.Label(frame_params, text="(越大越易找到)").pack(side="left", padx=5)
        
        # ---------- 控制按钮 ----------
        frame_btn = tk.Frame(left_frame)
        frame_btn.pack(pady=8)
        
        self.btn_generate = tk.Button(frame_btn, text="开始搜索", command=self.run_search,
                                       bg="#4CAF50", fg="white", font=("Arial", 11), padx=30, pady=6)
        self.btn_generate.pack(side="left", padx=5)
        
        self.btn_stop = tk.Button(frame_btn, text="停止搜索", command=self.stop_search,
                                   bg="#f44336", fg="white", font=("Arial", 11), padx=30, pady=6)
        self.btn_stop.pack(side="left", padx=5)
        self.btn_stop.config(state="disabled")
        
        # ---------- 进度 ----------
        self.progress_label = tk.Label(left_frame, text="等待开始...", font=("Arial", 9), fg="blue")
        self.progress_label.pack(pady=3)
        
        # -------- 右侧：排布结果（适当缩小） --------
        right_frame = tk.Frame(main_frame, width=500)
        right_frame.pack(side="right", fill="both", expand=True)
        right_frame.pack_propagate(False)
        
        frame_result = tk.LabelFrame(right_frame, text="排布结果", padx=8, pady=5)
        frame_result.pack(fill="both", expand=True)
        
        self.result_text = scrolledtext.ScrolledText(frame_result, height=28, font=("Courier", 9))
        self.result_text.pack(fill="both", expand=True)
        
        # 状态
        self.searching = False
        self.data_loaded = False
        
        # 检查是否需要自动加载
        if os.path.exists(self.data_path.get()):
            self.load_data()
        else:
            # 如果没有找到Excel，提示用户
            self.result_text.insert(tk.END, "未找到Excel数据文件。\n")
            self.result_text.insert(tk.END, "请点击'浏览'选择文件。\n")
    
    # ---------- 查找Excel文件 ----------
    def find_excel_file(self):
        """在同目录下查找Excel文件"""
        # 获取程序所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 查找所有Excel文件
        excel_files = []
        for ext in ['*.xlsx', '*.xls']:
            excel_files.extend(glob.glob(os.path.join(script_dir, ext)))
        
        if excel_files:
            # 如果找到多个，返回第一个
            return excel_files[0]
        
        # 检查示例文件
        sample_path = os.path.join(script_dir, "舞曲排布_示例.xlsx")
        if os.path.exists(sample_path):
            return sample_path
        
        return ""
    
    # ---------- 浏览文件 ----------
    def browse_file(self):
        """浏览选择Excel文件"""
        file_path = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=[("Excel文件", "*.xlsx *.xls"), ("所有文件", "*.*")]
        )
        if file_path:
            self.data_path.set(file_path)
            self.load_data()

    # ---------- 数据加载 ----------
    def load_data(self, show_message=True):
        path = self.data_path.get()
        
        # 如果路径为空或文件不存在
        if not path or not os.path.exists(path):
            if show_message:
                response = messagebox.askyesno(
                    "文件未找到",
                    f"未找到数据文件。"
                )
                if response:
                    sample_path = self.create_sample_excel()
                    if sample_path:
                        self.data_path.set(sample_path)
                        self.load_data(show_message=False)
                        return
            else:
                self.data_status.config(text="未加载", fg="red")
            return
        
        try:
            df = pd.read_excel(path, sheet_name="舞种配比", header=None, usecols="A:D", skiprows=1)
            df = df.dropna(how='all')
            
            global DATA, POOL, TOTAL
            DATA = []
            POOL = []
            
            for _, row in df.iterrows():
                cat = str(row[0]).strip()
                dance = str(row[1]).strip()
                rhythm = str(row[2]).strip()
                try:
                    count = int(row[3])
                except:
                    count = 1
                
                if cat and dance and rhythm:
                    DATA.append((cat, dance, rhythm, count))
                    for _ in range(count):
                        POOL.append((cat, dance, rhythm))
            
            TOTAL = len(POOL)
            self.data_status.config(text=f"已加载: {len(DATA)} 种, {TOTAL} 首", fg="green")
            self.data_loaded = True
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"✅ 数据加载成功！\n")
            self.result_text.insert(tk.END, f"文件: {os.path.basename(path)}\n")
            self.result_text.insert(tk.END, f"共 {len(DATA)} 个舞种，总计 {TOTAL} 首\n")
            self.result_text.insert(tk.END, "-" * 40 + "\n")
            for cat, dance, rhythm, count in DATA:
                self.result_text.insert(tk.END, f"{cat:<8} {dance:<12} {rhythm:<4} x{count}\n")
            
        except Exception as e:
            messagebox.showerror("加载失败", f"文件加载失败:\n{str(e)}\n\n请确保文件格式正确。")
            self.data_status.config(text="加载失败", fg="red")
    
    # ---------- 固定位置管理 ----------
    def apply_fixed_positions(self):
        self.fixed_positions = {}
        for pos_entry, dance_entry in self.fixed_entries:
            pos_text = pos_entry.get().strip()
            dance_text = dance_entry.get().strip()
            if pos_text and dance_text:
                try:
                    pos = int(pos_text)
                    self.fixed_positions[pos] = dance_text
                except:
                    pass
        self.update_fixed_display()
        messagebox.showinfo("提示", f"已应用 {len(self.fixed_positions)} 个固定位置")
    
    def clear_fixed_positions(self):
        self.fixed_positions = {}
        for pos_entry, dance_entry in self.fixed_entries:
            pos_entry.delete(0, tk.END)
            dance_entry.delete(0, tk.END)
        self.update_fixed_display()
    
    def update_fixed_display(self):
        if self.fixed_positions:
            self.data_status.config(text=f"已加载 + 固定: {self.fixed_positions}", fg="blue")
        else:
            self.data_status.config(text=f"已加载: {len(DATA)} 种, {TOTAL} 首", fg="green")
    
    # ---------- 约束检查 ----------
    def check_constraints(self, seq, rules):
        errors = []
        
        # 固定位置检查
        for pos, dance in self.fixed_positions.items():
            if pos < 1 or pos > len(seq):
                errors.append(f"固定位置 {pos} 超出范围")
            elif seq[pos-1][1] != dance:
                errors.append(f"位置 {pos} 应为 '{dance}'，实际为 '{seq[pos-1][1]}'")
        
        if rules.get('同舞种间隔', False):
            try:
                min_gap = int(self.gap_value.get())
            except:
                min_gap = 6
            last = {}
            for i, item in enumerate(seq):
                d = item[1]
                if d in last:
                    if i - last[d] < min_gap:
                        errors.append(f"'{d}' 位置 {last[d]+1} 和 {i+1} 间隔 {i-last[d]} < {min_gap}")
                last[d] = i
        
        if rules.get('大类不连续三次', False):
            for i in range(len(seq) - 2):
                if seq[i][0] == seq[i+1][0] == seq[i+2][0]:
                    errors.append(f"位置 {i+1}-{i+3} 大类连续三次: {seq[i][0]}")
        
        if rules.get('节奏约束', False):
            for i in range(len(seq) - 1):
                if seq[i][2] == "快" and seq[i+1][2] == "快":
                    errors.append(f"位置 {i+1}-{i+2} 快-快连续")
            for i in range(len(seq) - 2):
                if seq[i][2] == "中" and seq[i+1][2] == "中" and seq[i+2][2] == "中":
                    errors.append(f"位置 {i+1}-{i+3} 中速三连")
            for i in range(len(seq) - 2):
                if seq[i][2] == "慢" and seq[i+1][2] == "慢" and seq[i+2][2] == "慢":
                    errors.append(f"位置 {i+1}-{i+3} 慢速三连")
        
        return len(errors) == 0, errors
    
    # ---------- 生成序列 ----------
    def generate_sequence(self, rules, max_attempts=1):
        if not POOL:
            return None
        
        pool = POOL[:]
        fixed_pos = self.fixed_positions
        
        for _ in range(max_attempts):
            random.shuffle(pool)
            seq = pool[:]
            
            # 处理固定位置
            ok = True
            for pos, dance in fixed_pos.items():
                if pos < 1 or pos > len(seq):
                    ok = False
                    break
                if seq[pos-1][1] != dance:
                    swapped = False
                    for i in range(len(seq)):
                        if seq[i][1] == dance and i != pos-1:
                            seq[pos-1], seq[i] = seq[i], seq[pos-1]
                            swapped = True
                            break
                    if not swapped:
                        ok = False
                        break
            if not ok:
                continue
            
            if len(seq) != TOTAL:
                continue
            
            ok, _ = self.check_constraints(seq, rules)
            if ok:
                return seq
        
        return None
    
    # ---------- 搜索 ----------
    def stop_search(self):
        self.searching = False
        self.progress_label.config(text="已停止搜索")
        self.btn_generate.config(state="normal")
        self.btn_stop.config(state="disabled")
    
    def run_search(self):
        if not self.data_loaded:
            messagebox.showerror("错误", "请先加载数据！")
            return
        
        active_rules = {key: var.get() for key, var in self.rules.items()}
        
        try:
            gap = int(self.gap_value.get())
            if gap < 1:
                messagebox.showwarning("提示", "间隔值必须 ≥ 1")
                return
        except:
            messagebox.showwarning("提示", "请输入有效的间隔数字")
            return
        
        active_count = sum(active_rules.values())
        if active_count == 0 and not self.fixed_positions:
            messagebox.showwarning("提示", "请至少选择一条规则或设置固定位置！")
            return
        
        try:
            max_attempts = int(self.max_attempts.get())
        except:
            max_attempts = 50000
        
        self.btn_generate.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.searching = True
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "正在搜索，请稍候...\n")
        enabled = [k for k, v in active_rules.items() if v]
        self.result_text.insert(tk.END, f"已启用规则: {', '.join(enabled) if enabled else '无'}\n")
        self.result_text.insert(tk.END, f"同舞种间隔值: {self.gap_value.get()}\n")
        self.result_text.insert(tk.END, f"固定位置: {self.fixed_positions}\n")
        self.result_text.insert(tk.END, f"最大搜索次数: {max_attempts}\n")
        self.result_text.insert(tk.END, "-" * 50 + "\n")
        self.root.update()
        
        self._search_step(active_rules, 0, max_attempts)
    
    def _search_step(self, active_rules, attempt, max_attempts):
        if not self.searching:
            return
        
        if attempt >= max_attempts:
            self.result_text.insert(tk.END, "\n" + "=" * 50 + "\n")
            self.result_text.insert(tk.END, f"❌ 搜索 {max_attempts} 次未找到合法解。\n")
            self.result_text.insert(tk.END, "建议操作：\n")
            self.result_text.insert(tk.END, "  1. 取消勾选 '节奏约束'（如果已启用）\n")
            self.result_text.insert(tk.END, "  2. 将 '同舞种间隔值' 调低（如从6降到5或4）\n")
            self.result_text.insert(tk.END, "  3. 增加 '最大搜索次数'（如 100000）\n")
            self.result_text.insert(tk.END, "  4. 减少固定位置数量\n")
            self.progress_label.config(text=f"搜索失败，已尝试 {max_attempts} 次")
            self.btn_generate.config(state="normal")
            self.btn_stop.config(state="disabled")
            return
        
        if attempt % 500 == 0:
            self.progress_label.config(text=f"正在搜索... 已尝试 {attempt} 次")
            self.root.update()
        
        seq = self.generate_sequence(active_rules, max_attempts=1)
        
        if seq is not None:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"✅ 找到合法解！(尝试 {attempt+1} 次)\n")
            self.result_text.insert(tk.END, "-" * 50 + "\n")
            self.result_text.insert(tk.END, f"{'序号':<4} {'大类':<8} {'舞种':<12} {'节奏':<4}\n")
            self.result_text.insert(tk.END, "-" * 50 + "\n")
            for i, (cat, dance, rhythm) in enumerate(seq, 1):
                self.result_text.insert(tk.END, f"{i:<4} {cat:<8} {dance:<12} {rhythm:<4}\n")
            
            # 舞种列输出
            self.result_text.insert(tk.END, "\n" + "-" * 50 + "\n")
            self.result_text.insert(tk.END, "【仅舞种列表】（复制下面这段到excel里使用）\n")
            self.result_text.insert(tk.END, "-" * 50 + "\n")
            dance_list = [dance for _, dance, _ in seq]
            self.result_text.insert(tk.END, "、".join(dance_list) + "\n")
            self.result_text.insert(tk.END, "-" * 50 + "\n")
            self.result_text.insert(tk.END, f"共 {len(dance_list)} 首\n")
            
            ok, errors = self.check_constraints(seq, active_rules)
            self.result_text.insert(tk.END, "\n" + "-" * 50 + "\n")
            if ok:
                self.result_text.insert(tk.END, "✅ 所有启用的规则均已通过校验\n")
            else:
                self.result_text.insert(tk.END, f"⚠️ 发现 {len(errors)} 个问题:\n")
                for e in errors[:10]:
                    self.result_text.insert(tk.END, f"  - {e}\n")
            
            self.progress_label.config(text=f"搜索成功！共尝试 {attempt+1} 次")
            self.btn_generate.config(state="normal")
            self.btn_stop.config(state="disabled")
            self.searching = False
            return
        
        self.root.after(5, self._search_step, active_rules, attempt + 1, max_attempts)


# ---------- 启动 ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = PlaylistApp(root)
    root.mainloop()