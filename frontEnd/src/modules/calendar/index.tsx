import Calendar18 from "@/components/calendar-18";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

const Calendar = () => {
    return (
        <div className="flex flex-col md:flex-row w-full bg-gradient-to-b from-yellow-100 to-white p-4 md:p-8">
            <main className="w-full md:w-4/5 p-0 md:pr-4"> 
                <div className="mb-6">
                    <h1 className="text-2xl md:text-3xl font-bold text-center md:text-left mb-1">Agenda climática</h1>
                    <p className="text-center md:text-left text-sm md:text-base">
                        Planeje seus eventos com inteligência meteorológica
                    </p>
                    <div className="flex justify-center mt-4 w-full">
                        <Calendar18 />
                    </div> 
                </div>
            </main>
            
            <section className="w-full md:w-1/5 py-2 md:py-3 px-0 space-y-4 md:space-y-6">
                
                <div className="flex justify-center w-full">
                    <Button className="bg-blue-500 rounded-full w-2/3 md:w-full py-2 min-w-44 mb-2 flex items-center justify-center text-white">
                        <Plus className="mr-2 h-4 w-4" />
                        Novo Evento
                    </Button>
                </div>
                
                <div className="p-4 bg-white rounded-xl shadow-xl border border-gray-200 w-full max-w-sm mx-auto md:max-w-none md:mx-0">
                    <div className="flex items-center mb-4">
                        <span className="text-indigo-600 mr-2 text-xl">🌡️</span>
                        <h2 className="text-lg font-semibold text-gray-800">Resumo Semanal</h2>
                    </div>
                    <div className="grid grid-cols-2 gap-y-4 gap-x-2 text-center">
                        <div className="flex flex-col items-center">
                            <span className="text-orange-400 text-1xl mb-1">
                                ☀️
                            </span>
                            <p className="text-sm text-gray-600">Dias de sol</p>
                            <p className="text-xl font-bold text-gray-800">4</p>
                        </div>

                        <div className="flex flex-col items-center">
                            <span className="text-blue-400 text-1xl mb-1">
                                🌧️
                            </span>
                            <p className="text-sm text-gray-600">Dias de Chuva</p>
                            <p className="text-xl font-bold text-gray-800">2</p>
                        </div>

                        <div className="flex flex-col items-center">
                            <span className="text-green-500 text-1xl mb-1">
                                🌡️
                            </span>
                            <p className="text-sm text-gray-600">Temp. Média</p>
                            <p className="text-xl font-bold text-gray-800">24°C</p>
                        </div>

                        <div className="flex flex-col items-center">
                            <span className="text-purple-500 text-1xl mb-1">
                                🔔
                            </span>
                            <p className="text-sm text-gray-600">Alertas</p>
                            <p className="text-xl font-bold text-gray-800">0</p>
                        </div>
                    </div>
                </div>

                <div className="p-4 bg-white rounded-xl shadow-xl border border-gray-200 w-full max-w-sm mx-auto md:max-w-none md:mx-0">
                    <h2 className="text-xl font-bold mb-4">Eventos do dia</h2>
                    <p>Nenhum evento agendado para esta data</p>
                </div>

                <div className="p-4 bg-white rounded-xl shadow-xl border border-gray-200 w-full max-w-sm mx-auto md:max-w-none md:mx-0">
                    <h2 className="text-xl font-xl font-bold mb-4">Próximos eventos</h2>
                    <p>Nenhum evento futuro</p>
                </div>

                <Button className="rounded-full w-full py-8 bg-gradient-to-r from-yellow-300 to-blue-500 text-gray-900 text-lg">
                    Recomendação por IA
                </Button>
            </section>
        </div>
    );
};

export default Calendar;