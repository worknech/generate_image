import asyncio
import tkinter as tk
from tkinter import ttk, messagebox
from threading import Thread
from g4f.client import AsyncClient


class ImageGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Генератор изображений')
        self.root.geometry('600x400')

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

        # Поле для ссылки
        ttk.Label(self.root, text="Ссылка на изображение:").pack(pady=5)
        self.url_label = ttk.Label(self.root, text="Здесь появится ссылка...", wraplength=550, justify="left",
                                        foreground="blue")
        self.url_label.pack(pady=5, padx=20, fill="x")

        # Кнопка копирования
        self.copy_btn = ttk.Button(self.root, text="Копировать ссылку", command=self.copy_url, state="disabled")
        self.copy_btn.pack(pady=5)

    def start_generation(self):
        prompt = self.prompt_entry.get().strip()
        if not prompt:
            messagebox.showwarning("Внимание", "Введите промпт для генерации")
            return

        # Блокируем кнопку и показываем прогресс
        self.generate_btn.config(state="disabled")
        self.progress.pack(pady=10)
        self.progress.start()
        self.url_label.config(text="Генерация изображения...")

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
        self.copy_btn.config(state="normal")

        # Показываем ссылку
        self.url_label.config(text=image_url)

        # Сообщение об успехе
        messagebox.showinfo("Успех", "Изображение успешно сгенерировано!")

    def on_generation_error(self, error_message):
        # Останавливаем прогресс и обновляем UI
        self.progress.stop()
        self.progress.pack_forget()
        self.generate_btn.config(state="normal")
        self.copy_btn.config(state="disabled")

        # Показываем ошибку
        self.url_label.config(text=f"Ошибка: {error_message}", foreground="red")
        messagebox.showerror("Ошибка", f"Произошла ошибка при генерации:\n{error_message}")

    def copy_url(self):
        url = self.url_label.cget("text")
        if url and url != "Здесь появится ссылка..." and not url.startswith("Ошибка"):
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            messagebox.showinfo("Скопировано", "Ссылка скопирована в буфер обмена")

def main():
    root = tk.Tk()
    app = ImageGeneratorApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
