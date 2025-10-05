const weatherData = {
  location: "São Paulo, SP",
  temperature: 24,
  feelsLike: 27,
  rainStatus: "Chuva forte",
  humidity: 65,
  wind: "12 km/h",
  visibility: "10 km",
  uvIndex: 6,
};

const weekForecast = [
  {
    day: "Hoje",
    max: 28,
    min: 18,
    description: "Ensolarado",
    rainChance: null,
    icon: "☀️",
  },
  {
    day: "Dom",
    max: 26,
    min: 16,
    description: "Parcialmente nublado",
    rainChance: "10% chuva",
    icon: "🌥️",
  },
  {
    day: "Seg",
    max: 22,
    min: 14,
    description: "Chuva leve",
    rainChance: "70% chuva",
    icon: "🌧️",
  },
  {
    day: "Ter",
    max: 25,
    min: 17,
    description: "Nublado",
    rainChance: "20% chuva",
    icon: "☁️",
  },
  {
    day: "Qua",
    max: 29,
    min: 19,
    description: "Ensolarado",
    rainChance: null,
    icon: "☀️",
  },
  {
    day: "Qui",
    max: 31,
    min: 21,
    description: "Muito quente",
    rainChance: null,
    icon: "☀️",
  },
  {
    day: "Sex",
    max: 20,
    min: 12,
    description: "Tempestade",
    rainChance: "90% chuva",
    icon: "⚡",
  },
];

const Clima = () => {
  return (
    <div className="bg-gradient-to-t from-[#F8FBFF] via-[#FFEDDB] to-[#FFDFD2] flex flex-col w-full h-full justify-around gap-7 p-30 font-sans text-gray-900">
      <div className="flex flex-col md:flex-row md:space-x-6 mb-8">
        {/* Card principal */}
        <div className="bg-white rounded-xl shadow-md p-6 flex-1 w-full">
          <div className="text-sm text-gray-600 flex items-center mb-2">
            <svg
              className="w-4 h-4 mr-1"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M17.657 16.657L13.414 12.414 17.657 8.171M6 14a8 8 0 1111.313-11.313"
              ></path>
            </svg>
            {weatherData.location}
          </div>
          <div className="flex items-center space-x-6 mb-3">
            <span className="text-6xl font-extrabold bg-gradient-to-br from-blue-500 to-purple-600 text-transparent bg-clip-text">
              {weatherData.temperature}°
            </span>
            <div className="space-y-2">
              <div className="flex items-center space-x-1 text-gray-700">
                <svg
                  className="w-5 h-5 text-blue-600"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path d="M12 2C8.13 2 5 5.13 5 9c0 3.87 7 13 7 13s7-9.13 7-13c0-3.87-3.13-7-7-7z" />
                </svg>
                <span className="text-sm">
                  Sensação térmica: {weatherData.feelsLike}°
                </span>
              </div>
              <button className="text-blue-600 font-semibold text-sm hover:underline cursor-pointer flex items-center space-x-1">
                <svg
                  className="w-4 h-4"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    fillRule="evenodd"
                    d="M2 10a8 8 0 1116 0 8 8 0 01-16 0zm9-3v4h4v-4h-4z"
                    clipRule="evenodd"
                  />
                </svg>
                <span>{weatherData.rainStatus}</span>
              </button>
            </div>
          </div>
          {/* Grid informações */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-y-4 gap-x-10 text-center text-gray-700 font-medium text-sm">
            <div>
              <div className="flex justify-center mb-1">
                <svg
                  className="w-6 h-6 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path d="M12 3v1m0 16v1m8.485-10h-1M4.515 12h-1m12.364 6.364l-.707-.707m-9.9-9.9l-.707-.707m12.02 0l-.707.707m-9.9 9.9l-.707.707"></path>
                  <path d="M12 7a5 5 0 100 10 5 5 0 000-10z" />
                </svg>
              </div>
              <div>Umidade</div>
              <div className="font-bold">{weatherData.humidity}%</div>
            </div>
            <div>
              <div className="flex justify-center mb-1">
                <svg
                  className="w-6 h-6 text-green-500"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M16 3v10l-4-4-4 4V3"
                  />
                </svg>
              </div>
              <div>Vento</div>
              <div className="font-bold">{weatherData.wind}</div>
            </div>
            <div>
              <div className="flex justify-center mb-1">
                <svg
                  className="w-6 h-6 text-purple-600"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3 12h18M3 6h18M3 18h18"
                  />
                </svg>
              </div>
              <div>Visibilidade</div>
              <div className="font-bold">{weatherData.visibility}</div>
            </div>
            <div>
              <div className="flex justify-center mb-1">
                <svg
                  className="w-6 h-6 text-yellow-500"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 3v3M16.24 7.76l-2.12 2.12M21 12h-3M16.24 16.24l-2.12-2.12M12 21v-3M7.76 16.24l2.12-2.12M3 12h3M7.76 7.76l2.12 2.12"
                  />
                </svg>
              </div>
              <div>Índice UV</div>
              <div className="font-bold">{weatherData.uvIndex}</div>
            </div>
          </div>
        </div>

        {/* Card Agendar Evento */}
        <div className="bg-gradient-to-br from-blue-500 to-purple-700 text-white rounded-xl shadow-md p-6 mt-6 md:mt-0 w-auto  flex flex-col items-center justify-center ">
          <div className="bg-white bg-opacity-20 rounded-full p-3 mb-4">
            <svg
              className="w-8 h-8"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="16" y1="2" x2="16" y2="6"></line>
              <line x1="8" y1="2" x2="8" y2="6"></line>
              <line x1="3" y1="10" x2="21" y2="10"></line>
            </svg>
          </div>
          <h3 className="font-semibold text-lg mb-1">Agendar Evento</h3>
          <p className="text-center text-sm mb-4 px-4">
            Planeje seus compromissos com base na previsão do tempo
          </p>
          <button className="bg-white text-blue-600 px-5 py-2 rounded-full font-semibold hover:bg-blue-100 transition">
            Criar Evento &rarr;
          </button>
        </div>
      </div>

      {/* Previsão para 7 dias */}
      <h2 className="font-semibold text-gray-900 mb-4">
        Previsão para os próximos 7 dias
      </h2>
      <div className="bg-white rounded-xl shadow-md p-6  w-full overflow-x-auto">
        <div className="grid grid-cols-7 text-center gap-4 min-w-[600px]">
          {weekForecast.map(
            ({ day, max, min, description, rainChance, icon }, idx) => (
              <div
                key={idx}
                className="flex flex-col items-center text-sm text-gray-800"
              >
                <div className="text-2xl mb-1">{icon}</div>
                <div className="font-semibold">{max}°</div>
                <div className="text-xs text-gray-500 -mt-1">{min}°</div>
                <div className="mt-1">{description}</div>
                {rainChance && (
                  <div className="text-blue-600 font-semibold text-xs mt-1 cursor-pointer hover:underline">
                    {rainChance}
                  </div>
                )}
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
};

export default Clima;
