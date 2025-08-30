import asyncio
import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread
from PIL import Image, ImageTk
import requests
from io import BytesIO
from g4f.client import AsyncClient


class ImageGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Генератор изображений')
        self.root.geometry('600x300')

        self.setup_ui()

    def setup_ui(self):
        # Заголовок
        title_label = ttk.Label(self.root, text="Генератор изображений", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        # Промпт
        ttk.Label(self.root, text="Введите промпт:").pack(pady=5)
        self.prompt_entry = ttk.Entry(self.root, width=60)
        self.prompt_entry.pack(pady=5)
        self.prompt_entry.insert(0, "woman in dress")

        # Кнопка генерации
        self.generate_btn = ttk.Button(self.root, text="Сгенерировать изображение", command=self.start_generation)
        self.generate_btn.pack(pady=10)

        # Индикатор загрузки
        self.progress = ttk.Progressbar(self.root, mode='indeterminate')

    def start_generation(self):
        prompt = self.prompt_entry.get().strip()
        if not prompt:
            messagebox.showwarning("Внимание", "Введите промпт для генерации")
            return

        # Блокируем кнопку и показываем прогресс
        self.generate_btn.config(state="disabled")
        self.progress.pack(pady=10)
        self.progress.start()
        self.root.title('Генератор изображений - идёт генерация...')

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
            self.root.after(0, self.on_generation_success, result)
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

    def on_generation_success(self, image_url):
        # Останавливаем прогресс и обновляем UI
        self.progress.stop()
        self.progress.pack_forget()
        self.generate_btn.config(state="normal")
        self.root.title('Генератор изображений')

        # Загружаем и отображаем изображение
        self.download_and_show_image(image_url)

    def download_and_show_image(self, image_url):
        try:
            # Загружаем изображение из URL
            response = requests.get(image_url)
            response.raise_for_status()  # Проверяем на ошибки HTTP

            # Преобразуем байты в изображение PIL
            image_data =  BytesIO(response.content)
            pil_image = Image.open(image_data)

            # Создаем новое окно для отображения изображения
            self.show_image_window(pil_image, image_url)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить изображение:\n{str(e)}")

    def show_image_window(self, pil_image, image_url):
        # Создаем новое окно
        image_window = tk.Toplevel(self.root)
        image_window.title("Сгенерированное изображение")
        image_window.geometry('800x700')

        # Масштабируем изображение для отображения
        max_size = (600, 600)
        pil_image.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Конвертируем PIL Image в PhotoImage для Tkinter
        photo_image = ImageTk.PhotoImage(pil_image)

        # Создаем фрейм для содержимого
        content_frame = ttk.Frame(image_window)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Отображаем изображение
        image_label = ttk.Label(content_frame, image=photo_image)
        image_label.image = photo_image  # Сохраняем ссылку, чтобы избежать сборки мусора
        image_label.pack(pady=10)

        # Информация об изображении
        info_text = f"Размер: {pil_image.width}x{pil_image.height}px\nURL: {image_url}"
        info_label = ttk.Label(content_frame, text=info_text, justify=tk.LEFT)
        info_label.pack(pady=5)

        # Кнопка закрытия
        close_btn = ttk.Button(content_frame, text="Закрыть", command=image_window.destroy)
        close_btn.pack(pady=10)

        # Кнопка сохранения
        save_btn = ttk.Button(content_frame, text="Сохранить", command=lambda: self.save_image(pil_image))
        save_btn.pack(pady=5)

    def save_image(self,pil_image):
        # Диалог сохранения файла
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
        )

        if file_path:
            try:
                pil_image.save(file_path)
                messagebox.showinfo("Успех", f"Изображение сохранено как:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить изображение:\n{str(e)}")


    def on_generation_error(self, error_message):
        # Останавливаем прогресс и обновляем UI
        self.progress.stop()
        self.progress.pack_forget()
        self.generate_btn.config(state="normal")
        self.root.title('Генератор изображений')

        # Показываем ошибку
        messagebox.showerror("Ошибка", f"Произошла ошибка при генерации:\n{error_message}")


def main():
    root = tk.Tk()
    app = ImageGeneratorApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
