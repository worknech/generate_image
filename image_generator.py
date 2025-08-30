import asyncio
from g4f.client import AsyncClient


async def main():
    client = AsyncClient()

    response = await client.images.generate(
        prompt='woman in dress',
        model='flux',
        response_format='url',  # Получить URL изображения
        size='1024x1024',
        style='photorealistic'
    )

    image_url = response.data[0].url
    print(f'Generated image URL: {image_url}')

# Запуск асинхронной функции
if __name__ == '__main__':
    asyncio.run(main())