from weather import WeatherFacade, WeatherError
from database import WeatherHistory
from strategies import (
    WalkStrategy,
    ClothingStrategy,
    PrecipitationStrategy,
)

STRATEGIES = {
    "1": ("Планування прогулянки", WalkStrategy()),
    "2": ("Вибір одягу", ClothingStrategy()),
    "3": ("Підготовка до опадів", PrecipitationStrategy()),
}

def print_forecast(forecast):
    print(f"\nПрогноз для міста: {forecast.city}")
    print(f"Координати: {forecast.latitude:.4f}, {forecast.longitude:.4f}")
    print("-" * 55)

    for item in forecast.hours[:3]:
        probability = (
            f"{item.precipitation_probability}%"
            if item.precipitation_probability is not None
            else "немає даних"
        )
        print(
            f"{item.time}: {item.temperature_c:.1f} °C, "
            f"ймовірність опадів: {probability}"
        )



def choose_strategy(forecast):
    while True:
        print("\n=== ОБЕРІТЬ СТРАТЕГІЮ ===")
        print("1. Планування прогулянки")
        print("2. Вибір одягу")
        print("3. Підготовка до опадів")

        choice = input("Ваш вибір: ").strip()

        if choice in STRATEGIES:
            name, strategy = STRATEGIES[choice]

            print(f"\n=== СТРАТЕГІЯ: {name.upper()} ===")

            recommendations = strategy.recommend(forecast)

            for recommendation in recommendations:
                print(f"Рекомендація: {recommendation}")

        else:
            print("Невідомий вибір.")
            continue

        print("\n=== ЩО РОБИМО ДАЛІ? ===")
        print("1. Обрати ще одну стратегію")
        print("2. Обрати інше місто")
        print("3. Повернутися до головного меню")
        print("0. Вийти з програми")

        next_choice = input("Ваш вибір: ").strip()

        if next_choice == "1":
            continue
        elif next_choice == "2":
            return "city"
        elif next_choice == "3":
            return "menu"
        elif next_choice == "0":
            return "exit"
        else:
            print("Невідомий вибір. Повертаємося до стратегій.")


def show_history(history):
    city = input("Введіть назву міста або залиште порожнім для всіх міст: ").strip()
    try:
        records = history.get_recent(city=city or None, limit=20)
    except Exception as error:
        print(f"Не вдалося прочитати історію: {error}")
        return

    if not records:
        print("Історія поки порожня.")
        return

    print("\nОстанні записи історії:")
    for row in records:
        print(
            f"#{row['id']} | {row['city']} | отримано: {row['retrieved_at']} | "
            f"прогноз: {row['forecast_time']} | {row['temperature_c']:.1f} °C | "
            f"опади: {row['precipitation_probability'] if row['precipitation_probability'] is not None else 'немає даних'}%"
        )


def main():
    history = WeatherHistory()
    facade = WeatherFacade(history=history)

    print("=== Weather Assistant ===")

    while True:
        print("\n1. Отримати прогноз погоди")
        print("2. Переглянути історію")
        print("3. Показати кількість HTTP-запитів прогнозу")
        print("0. Вийти")

        choice = input("Ваш вибір: ").strip()

        if choice == "1":
            city = input("Введіть назву міста (наприклад, Lviv): ").strip()
            if not city:
                print("Назва міста не може бути порожньою.")
                continue

            try:
                forecast = facade.get_weather(city)
                print_forecast(forecast)
                choose_strategy(forecast)
                print(
                    "\nДані збережено в історії. "
                    f"Кеш: {'використано' if facade.last_cache_hit else 'оновлено'}."
                )
            except WeatherError as error:
                print(f"Помилка отримання погоди: {error}")
            except Exception as error:
                print(f"Сталася неочікувана помилка: {error}")

        elif choice == "2":
            show_history(history)

        elif choice == "3":
            print(
                "Кількість фактичних HTTP-запитів до API прогнозу "
                f"в цій сесії: {facade.forecast_provider.http_requests}"
            )
            print("Порада: повторіть запит для того самого міста в межах 10 хвилин.")

        elif choice == "0":
            print("До побачення!")
            break

        else:
            print("Невідомий пункт меню. Спробуйте ще раз.")


if __name__ == "__main__":
    main()
