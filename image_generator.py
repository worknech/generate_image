import asyncio
import os.path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from threading import Thread
from urllib.parse import urlparse
from tkinter import filedialog
from PIL import Image, ImageTk
import requests
from io import BytesIO
from g4f.client import AsyncClient


class ImageGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Генератор изображений')
        self.root.geometry('700x500')
        self.root.minsize(600, 400)  # Минимальный размер окна
        self.tooltip = None

        # Центрирование окна
        self.center_window()

        # Доступные модели
        self.available_models = [
            'flux',
            'stable_diffusion_3',
            'sdxl_lightning',
            'dall-e',
            'playground_v2.5'
        ]

        # Доступные соотношения сторон
        self.aspect_ratios = {
            '1:1': '1024x1024',
            '3:4': '768x1024',
            '9:16': '576x1024'
        }

        # Модели, которые поддерживают изменение размера
        self.models_supporting_size = ['flux', 'stable_diffusion_3', 'sdxl_lightning', 'playground_v2.5']

        # Текущая выбранная модель
        self.selected_model = tk.StringVar(value=self.available_models[0])
        # Текущее выбранное соотношение сторон
        self.selected_ratio = tk.StringVar(value='1:1')

        self.setup_ui()

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_ui(self):
        # Главный фрейм для управления макетом
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = ttk.Label(main_frame, text="Генератор изображений", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 15))

        # Фрейм для выбора модели
        model_frame = ttk.Frame(main_frame)
        model_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(model_frame, text="Модель генерации:").pack(anchor=tk.W)

        # Combobox для выбора модели
        model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.selected_model,
            values=self.available_models,
            state="readonly",
            font=("Arial", 10)
        )
        model_combo.pack(fill=tk.X, pady=(5, 0))

        # Подсказка при наведении
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.withdraw()
        self.tooltip_label = ttk.Label(self.tooltip, text="", background="lightyellow", relief="solid", borderwidth=1)
        self.tooltip_label.pack()

        def show_tooltip(event):
            model = self.selected_model.get()
            tooltip_text = self.get_model_description(model)
            self.tooltip_label.config(text=tooltip_text)
            self.tooltip.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            self.tooltip.deiconify()

        def hide_tooltip(event):
            self.tooltip.withdraw()

        model_combo.bind("<Enter>", show_tooltip)
        model_combo.bind("<Leave>", hide_tooltip)

        # Фрейм для выбора соотношения сторон
        ratio_frame = ttk.Frame(main_frame)
        ratio_frame.pack(fill=tk.X, pady=(10, 15))

        ttk.Label(ratio_frame, text="Соотношение сторон:").pack(anchor=tk.W)

        # Radiobuttons для выбора соотношения сторон
        ratio_container = ttk.Frame(ratio_frame)
        ratio_container.pack(fill=tk.X, pady=(5, 0))

        ttk.Radiobutton(ratio_container, text="1:1 (Квадрат)", variable=self.selected_ratio, value='1:1').pack(
            side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(ratio_container, text="3:4 (Портрет)", variable=self.selected_ratio, value='3:4').pack(
            side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(ratio_container, text="9:16 (Вертикальное)", variable=self.selected_ratio, value='9:16').pack(
            side=tk.LEFT)

        #  Фрейм для промпта
        prompt_frame = ttk.Frame(main_frame)
        prompt_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Промпт
        ttk.Label(prompt_frame, text="Введите промпт:").pack(anchor=tk.W)

        # Создаем фрейм для текстового поля и скроллбаров
        text_frame = ttk.Frame(prompt_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # Многострочное текстовое поле с прокруткой
        self.prompt_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,  # Перенос слов
            font=("Arial", 11),
            height=6,  # Высота в строках
            padx=5,
            pady=5
        )
        self.prompt_text.pack(fill=tk.BOTH, expand=True)
        self.prompt_text.insert('1.0', "woman in dress")

        # Бинд Ctrl+Enter для быстрой генерации (ДОБАВЬТЕ ЭТУ СТРОЧКУ)
        self.prompt_text.bind('<Control-Return>', lambda e: self.start_generation())

        # Кнопка генерации
        self.generate_btn = ttk.Button(main_frame, text="Сгенерировать изображение",
                                       command=self.start_generation,
                                       style="Accent.TButton")
        self.generate_btn.pack(pady=15)

        # Индикатор загрузки
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')

        # Статус бар внизу окна
        self.status_var = tk.StringVar()
        self.status_var.set("Готов к генерации")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def get_model_description(self, model):
        """Возвращает описание модели для подсказки"""
        descriptions = {
            'flux': 'FLUX - поддерживает разные размеры, хорошее качество',
            'stable_diffusion_3': 'Stable Diffusion 3 - поддерживает разные размеры, текст в изображениях',
            'sdxl_lightning': 'SDXL Lightning - быстрая генерация, поддерживает размеры',
            'dall-e': 'DALL-E - может не поддерживать все размеры, требует ключ API',
            'playground_v2.5': 'Playground v2.5 - поддерживает размеры, стилизованные изображения'
        }
        return descriptions.get(model, 'Описание модели недоступно')

    def start_generation(self):
        prompt = self.prompt_text.get('1.0', tk.END).strip()
        model = self.selected_model.get()
        ratio = self.selected_ratio.get()

        if not prompt:
            messagebox.showwarning("Внимание", "Введите промпт для генерации")
            return

        # Проверяем, поддерживает ли модель изменение размера
        if model not in self.models_supporting_size and ratio != '1:1':
            result = messagebox.askyesno(
                "Предупреждение",
                f"Модель {model} может не поддерживать соотношение {ratio}. "
                f"Может быть сгенерировано квадратное изображение. Продолжить?"
            )
            if not result:
                return

        # Блокируем кнопку и показываем прогресс
        self.generate_btn.config(state="disabled")
        self.prompt_text.config(state="disabled")
        self.progress.pack(pady=10)
        self.progress.start()
        self.root.title(f'Генератор изображений - {model} - идёт генерация...')
        self.status_var.set(f"Генерация изображения с помощью {model} ({ratio})...")

        # Запускаем асинхронную задачу в отдельном потоке
        thread = Thread(target=self.run_async_task, args=(prompt, model, ratio))
        thread.daemon = True
        thread.start()

    def run_async_task(self, prompt, model, ratio):
        # Создаем новый event loop для потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(self.generate_image(prompt, model, ratio))
            self.root.after(0, self.on_generation_success, result, prompt, model, ratio)
        except Exception as e:
            self.root.after(0, self.on_generation_error, str(e), model, ratio)
        finally:
            loop.close()

    async def generate_image(self, prompt, model, ratio):
        client = AsyncClient()

        # Базовые параметры для всех моделей
        params = {
            'prompt': prompt,
            'model': model,
            'response_format': 'url'
        }

        # Добавляем размер только для моделей, которые его поддерживают
        if model in self.models_supporting_size:
            params['size'] = self.aspect_ratios[ratio]

        # Специфические параметры для разных моделей
        if model == 'flux':
            params['style'] = 'photorealistic'
        elif model == 'dall-e':
            # Для DALL-E пробуем указать размер, но он может игнорироваться
            if ratio != '1:1':
                params['size'] = self.aspect_ratios[ratio]

        try:
            response = await client.images.generate(**params)
            image_url = response.data[0].url
            return image_url
        except Exception as e:
            # Если произошла ошибка, пробуем сгенерировать с размером по умолчанию
            if 'size' in params and model != 'dall-e':
                del params['size']
                response = await client.images.generate(**params)
                image_url = response.data[0].url
                return image_url
            raise e

    def on_generation_success(self, image_url, prompt, model, ratio):
        # Останавливаем прогресс и обновляем UI
        self.progress.stop()
        self.progress.pack_forget()
        self.generate_btn.config(state="normal")
        self.prompt_text.config(state="normal")
        self.root.title('Генератор изображений')
        self.status_var.set(f"Генерация завершена ({model}, {ratio})")

        # Загружаем и отображаем изображение
        self.download_and_show_image(image_url, prompt, model, ratio)

    def download_and_show_image(self, image_url, prompt, model, ratio):
        try:
            self.status_var.set("Загрузка изображения...")

            # Загружаем изображение из URL
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()  # Проверяем на ошибки HTTP

            # Преобразуем байты в изображение PIL
            image_data =  BytesIO(response.content)
            pil_image = Image.open(image_data)

            # Проверяем фактическое соотношение сторон
            actual_ratio = f"{pil_image.size[0]}:{pil_image.size[1]}"
            expected_ratio = self.aspect_ratios[ratio]

            if ratio != '1:1' and actual_ratio != expected_ratio:
                self.status_var.set(f"Внимание: получено {actual_ratio} вместо {ratio}")

            # Создаем новое окно для отображения изображения
            self.show_image_window(pil_image, image_url, prompt, model, ratio, actual_ratio)

            self.status_var.set("Изображение загружено")

        except requests.exceptions.Timeout:
            messagebox.showerror("Ошибка", "Таймаут при загрузке изображения")
            self.status_var.set("Ошибка: таймаут")
            self.prompt_text.config(state="normal")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить изображение:\n{str(e)}")
            self.status_var.set("Ошибка загрузки")
            self.prompt_text.config(state="normal")

    def show_image_window(self, pil_image, image_url, prompt, model, ratio, actual_ratio=None):
        # Создаем новое окно
        image_window = tk.Toplevel(self.root)
        title = f"Сгенерированное изображение - {model} ({ratio})"
        if actual_ratio and actual_ratio != self.aspect_ratios[ratio]:
            title += f" (фактически: {actual_ratio})"
        image_window.title(title)
        image_window.geometry('800x700')
        image_window.minsize(700, 600)

        # Центрируем окно изображения
        image_window.transient(self.root)
        image_window.grab_set()

        # Создаём панель с вкладками
        notebook = ttk.Notebook(image_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Вкладка с изображением
        image_frame = ttk.Frame(notebook)
        notebook.add(image_frame, text="Изображение")

        # Масштабируем изображение для отображения
        max_size = (700, 700)
        pil_image.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Конвертируем PIL Image в PhotoImage для Tkinter
        photo_image = ImageTk.PhotoImage(pil_image)

        # Canvas для изображения с прокруткой
        canvas = tk.Canvas(image_frame)
        scrollbar_y = ttk.Scrollbar(image_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar_x = ttk.Scrollbar(image_frame, orient=tk.HORIZONTAL, command=canvas.xview)

        canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        # Фрейм внутри canvas для изображения
        image_container = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=image_container, anchor=tk.NW)

        # Отображаем изображение
        image_label = ttk.Label(image_container, image=photo_image)
        image_label.image = photo_image  # Сохраняем ссылку, чтобы избежать сборки мусора
        image_label.pack(pady=10)

        # Обновляем scrollregion после отображения изображения
        def configure_canvas(event):
            canvas.configure(scrollregion=canvas.bbox('all'))

        image_container.bind("<Configure>", configure_canvas)

        # Размещаем элементы
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Вкладка с информацией
        info_frame = ttk.Frame(notebook)
        notebook.add(info_frame, text="Информация")

        info_text = f"""Модель: {model}
Запрошенное соотношение: {ratio}
Фактическое соотношение: {actual_ratio if actual_ratio else 'неизвестно'}
Промпт: {prompt}

Размер оригинала: {pil_image.size[0]}x{pil_image.size[1]}px
Формат: {pil_image.format}
Режим: {pil_image.mode}

URL изображения: {image_url}
Домен: {urlparse(image_url).netloc}"""

        info_label = ttk.Label(info_frame, text=info_text, justify=tk.LEFT, padding=10)
        info_label.pack(anchor=tk.W, pady=10)

        # Панель кнопок
        button_frame = ttk.Frame(image_window)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(button_frame, text="Сохранить",
                   command=lambda: self.save_image(pil_image)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Новая генерация",
                   command=lambda: self.new_generation(image_window)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Закрыть",
                   command=image_window.destroy).pack(side=tk.RIGHT, padx=5)

    def new_generation(self, image_window):
        """Закрывает окно изображения и разрешает новую генерацию"""
        image_window.destroy()
        self.prompt_text.focus()
        self.prompt_text.tag_add(tk.SEL, "1.0", tk.END)
        self.prompt_text.mark_set(tk.INSERT, "1.0")

    def save_image(self,pil_image):
        # Генерируем предлагаемое имя файла на основе промпта
        prompt_text = self.prompt_text.get('1.0', tk.END).strip()[:50]
        model = self.selected_model.get()
        ratio = self.selected_ratio.get()
        safe_name = "".join(c if c.isalnum() else "_" for c in prompt_text)
        default_name = f"generated_{safe_name}_{model}_{ratio.replace(':', 'x')}.jpg"

        file_path = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=".jpg",
            filetypes=[
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg"),
                ("All files", "*.*")

                ]
        )

        if file_path:
            try:
                # Определяем формат based on extension
                format = os.path.splitext(file_path)[1][1:].upper()
                if format == 'JPG':
                    format = 'JPEG'

                pil_image.save(file_path, format=format if format in ['PNG', 'JPEG'] else 'PNG')
                messagebox.showinfo("Успех", f"Изображение сохранено как:\n{file_path}")
                self.status_var.set(f"Изображение сохранено: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить изображение:\n{str(e)}")
                self.status_var.set("Ошибка сохранения")

    def on_generation_error(self, error_message, model, ratio):
        # Останавливаем прогресс и обновляем UI
        self.progress.stop()
        self.progress.pack_forget()
        self.generate_btn.config(state="normal")
        self.prompt_text.config(state="normal")
        self.root.title('Генератор изображений')
        self.status_var.set(f"Ошибка генерации ({model}, {ratio}))")

        # Показываем ошибку
        messagebox.showerror("Ошибка", f"Произошла ошибка при генерации с помощью {model} ({ratio})"
                                       f":\n{error_message}")


def main():
    root = tk.Tk()

    # Настраиваем стиль для акцентной кнопки
    style = ttk.Style()
    style.configure("Accent.TButton", font=('Arial', 11, 'bold'))
    app = ImageGeneratorApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
