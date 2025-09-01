import asyncio
import os.path
import tkinter as tk
from tkinter import ttk, messagebox
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
        self.root.geometry('600x300')
        self.root.minsize(500, 200)  # Минимальный размер окна

        # Центрирование окна
        self.center_window()

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
        title_label.pack(pady=(0, 20))

        #  Фрейм для промпта
        prompt_frame = ttk.Frame(main_frame)
        prompt_frame.pack(fill=tk.X, pady=(0, 15))

        # Промпт
        ttk.Label(prompt_frame, text="Введите промпт:").pack(anchor=tk.W)
        self.prompt_entry = ttk.Entry(prompt_frame, font=("Arial", 11))
        self.prompt_entry.pack(fill=tk.X, pady=(5, 0))
        self.prompt_entry.insert(0, "woman in dress")

        # Бинд Enter для быстрой генерации
        self.prompt_entry.bind('<Return>', lambda e: self.start_generation())

        # Кнопка генерации
        self.generate_btn = ttk.Button(main_frame, text="Сгенерировать изображение",
                                       command=self.start_generation,
                                       style="Accent.TButton")
        self.generate_btn.pack(pady=20)

        # Индикатор загрузки
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')

        # Статус бар внизу окна
        self.status_var = tk.StringVar()
        self.status_var.set("Готов к генерации")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def start_generation(self):
        prompt = self.prompt_entry.get().strip()
        if not prompt:
            messagebox.showwarning("Внимание", "Введите промпт для генерации")
            return

        # Блокируем кнопку и показываем прогресс
        self.generate_btn.config(state="disabled")
        self.prompt_entry.config(state="disabled")
        self.progress.pack(pady=10)
        self.progress.start()
        self.root.title('Генератор изображений - идёт генерация...')
        self.status_var.set("Генерация изображения...")

        # Запускаем асинхронную задачу в отдельном потоке
        thread = Thread(target=self.run_async_task, args=(prompt,))
        thread.daemon = True
        thread.start()

    def run_async_task(self, prompt):
        # Создаем новый event loop для потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(self.generate_image(prompt))
            self.root.after(0, self.on_generation_success, result, prompt)
        except Exception as e:
            self.root.after(0, self.on_generation_error, str(e))
        finally:
            loop.close()

    async def generate_image(self, prompt):
        client = AsyncClient()

        response = await client.images.generate(
            prompt=prompt,
            model='flux',
            response_format='url',  # Получить URL изображения
            size='1024x1024',
            style='photorealistic'
        )

        image_url = response.data[0].url
        return image_url

    def on_generation_success(self, image_url, prompt):
        # Останавливаем прогресс и обновляем UI
        self.progress.stop()
        self.progress.pack_forget()
        self.generate_btn.config(state="normal")
        self.prompt_entry.config(state="normal")
        self.root.title('Генератор изображений')
        self.status_var.set("Генерация завершена")

        # Загружаем и отображаем изображение
        self.download_and_show_image(image_url, prompt)

    def download_and_show_image(self, image_url, prompt):
        try:
            self.status_var.set("Загрузка изображения...")

            # Загружаем изображение из URL
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()  # Проверяем на ошибки HTTP

            # Преобразуем байты в изображение PIL
            image_data =  BytesIO(response.content)
            pil_image = Image.open(image_data)

            # Создаем новое окно для отображения изображения
            self.show_image_window(pil_image, image_url, prompt)

            self.status_var.set("Изображение загружено")

        except requests.exceptions.Timeout:
            messagebox.showerror("Ошибка", "Таймаут при загрузке изображения")
            self.status_var.set("Ошибка: таймаут")
            self.prompt_entry.config(state="normal")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить изображение:\n{str(e)}")
            self.status_var.set("Ошибка загрузки")
            self.prompt_entry.config(state="normal")

    def show_image_window(self, pil_image, image_url, prompt):
        # Создаем новое окно
        image_window = tk.Toplevel(self.root)
        image_window.title("Сгенерированное изображение")
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

        info_text = f"""Промпт: {prompt}

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
        self.prompt_entry.focus()
        self.prompt_entry.select_range(0, tk.END)

    def save_image(self,pil_image):
        # Генерируем предлагаемое имя файла на основе промпта
        prompt_text = self.prompt_entry.get().strip()[:50]
        safe_name = "".join(c if c.isalnum() else "_" for c in prompt_text)
        default_name = f"generated_{safe_name}.jpg" if safe_name else "generated_image.jpg"

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

    def on_generation_error(self, error_message):
        # Останавливаем прогресс и обновляем UI
        self.progress.stop()
        self.progress.pack_forget()
        self.generate_btn.config(state="normal")
        self.prompt_entry.config(state="normal")
        self.root.title('Генератор изображений')
        self.status_var.set("Ошибка генерации")

        # Показываем ошибку
        messagebox.showerror("Ошибка", f"Произошла ошибка при генерации:\n{error_message}")


def main():
    root = tk.Tk()

    # Настраиваем стиль для акцентной кнопки
    style = ttk.Style()
    style.configure("Accent.TButton", font=('Arial', 11, 'bold'))
    app = ImageGeneratorApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
