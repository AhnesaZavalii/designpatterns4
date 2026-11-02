from abc import ABC, abstractmethod


class RecommendationStrategy(ABC):

    @abstractmethod
    def recommend(self, forecast):
        pass


class WalkStrategy(RecommendationStrategy):

    def recommend(self, forecast):
        next_hours = forecast.hours[:3]
        average_temp = sum(hour.temperature_c for hour in next_hours) / len(next_hours)
        known_probs = [
            hour.precipitation_probability
            for hour in next_hours
            if hour.precipitation_probability is not None
        ]
        max_rain = max(known_probs) if known_probs else None

        if average_temp < 0:
            return [f"Для прогулянки холодно: середня температура {average_temp:.1f} °C."]
        if max_rain is not None and max_rain >= 60:
            return [f"Краще перенести прогулянку: імовірність опадів до {max_rain:.0f}%."]
        if average_temp >= 10 and (max_rain is None or max_rain < 30):
            return ["Погода загалом сприятлива для прогулянки."]
        return ["На прогулянку можна йти, але перевірте погоду та одягніться відповідно."]


class ClothingStrategy(RecommendationStrategy):

    def recommend(self, forecast):
        next_hours = forecast.hours[:3]
        average_temp = sum(hour.temperature_c for hour in next_hours) / len(next_hours)

        if average_temp < 0:
            advice = "Одягніть теплу зимову куртку, шапку, шарф і рукавички."
        elif average_temp < 10:
            advice = "Одягніть теплу куртку та закрите взуття."
        elif average_temp < 18:
            advice = "Підійде легка куртка або светр."
        elif average_temp < 25:
            advice = "Обирайте легкий одяг; за потреби візьміть тонкий верхній шар."
        else:
            advice = "Обирайте легкий, дихаючий одяг і не забувайте пити воду."

        return [f"Середня температура найближчих годин: {average_temp:.1f} °C.", advice]


class PrecipitationStrategy(RecommendationStrategy):

    def recommend(self, forecast):
        known_probs = [
            hour.precipitation_probability
            for hour in forecast.hours[:3]
            if hour.precipitation_probability is not None
        ]

        if not known_probs:
            return ["Немає даних про ймовірність опадів; перевірте прогноз перед виходом."]

        max_rain = max(known_probs)
        if max_rain >= 60:
            advice = "Візьміть парасольку або дощовик."
        elif max_rain >= 30:
            advice = "Можна взяти компактну парасольку про всяк випадок."
        else:
            advice = "Парасолька, ймовірно, не потрібна."

        return [f"Максимальна ймовірність опадів найближчих годин: {max_rain:.0f}%.", advice]
