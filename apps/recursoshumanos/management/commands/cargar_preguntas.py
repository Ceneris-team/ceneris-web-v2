# calidad/management/commands/cargar_preguntas.py

from django.core.management.base import BaseCommand
from recursoshumanos.models import Cuestionario, Pregunta

# Copia y pega aquí todas las preguntas de tus cuestionarios
PREGUNTAS_DISC = [
    # Fila 1
    "Entusiasta", "Rápido (a)", "Lógico (a)", "Apacible",
    # Fila 2
    "Cauteloso (a)", "Decidido (a)", "Receptivo (a)", "Bondadoso (a)",
    # Fila 3
    "Amigable", "Preciso (a)", "Franco (a)", "Tranquilo (a)",
    # Fila 4
    "Elocuente", "Controlado (a)", "Tolerante", "Decisivo (a)",
    # Fila 5
    "Atrevido (a)", "Concienzudo (a)", "Comunicativo (a)", "Moderado (a)",
    # Fila 6
    "Ameno (a)", "Ingenioso (a)", "Investigador (a)", "Acepta Riesgos (a)",
    # Fila 7
    "Expresivo (a)", "Cuidadoso (a)", "Domínate", "Sensible",
    # Fila 8
    "Extrovertido (a)", "Precavido (a)", "Constante", "Impaciente",
    # Fila 9
    "Discreto (a)", "Complaciente", "Encantador(a)", "Insistente",
    # Fila 10
    "Valeroso (a)", "Anima a los demas", "Pacifico (a)", "Perfeccionista",
    # Fila 11
    "Reservado (a)", "Atento (a)", "Osado (a)", "Alegre",
    # Fila 12
    "Estimulante", "Gentil", "Perceptivo (a)", "Independiente",
    # Fila 13
    "Competitivo (a)", "Considerado (a)", "Alegre", "Sagaz",
    # Fila 14
    "Meticuloso (a)", "Obediente (a)", "Ideas Firmes", "Alentador (a)",
    # Fila 15
    "Popular", "Reflexivo (a)", "Tenaz", "Calmado (a)",
    # Fila 16
    "Analítico (a)", "Audaz", "Leal", "Promotor",
    # Fila 17
    "Sociable", "Paciente", "Autosuficiente", "Certero (a)",
    # Fila 18
    "Adaptable", "Resuelto (a)", "Prevenido (a)", "Vivaz",
    # Fila 19
    "Agresivo (a)", "Impetuoso (a)", "Amistoso (a)", "Discerniente",
    # Fila 20
    "De trato facil", "Compasivo (a)", "Cauto (a)", "Habla Directo",
    # Fila 21
    "Evaluador (a)", "Generoso (a)", "Animado (a)", "Persistente",
    # Fila 22
    "Impulsivo (a)", "Cuida los Detalles", "Enérgico", "Tranquilo",
    # Fila 23
    "Sociable", "Sistemático (a)", "Vigoroso (a)", "Tolerante",
    # Fila 24
    "Cautivador (a)", "Contento (a)", "Exigente", "Apegado (a) a las normas",
    # Fila 25
    "Le agrega discutir", "Metódico (a)", "Comedido (a)", "Desenvuelto (a)",
    # Fila 26
    "Jovial", "Preciso (a)", "Directo (a)", "Ecuanime",
    # Fila 27
    "Inquieto (a)", "Amable", "Elocuente", "Cuidadoso (a)",
    # Fila 28
    "Prudente", "Pionero (a)", "Espontaneo (A)", "Colaborador",
]
PREGUNTAS_BIG_FIVE = [
    # Fila 1
    "Creo que soy una persona activa y vigorosa.",
    # Fila 2
    "No me gusta hacer las cosas razonando demasiado sobre ellas.",
    # Fila 3
    "Tiendo a involucrarme demasiado cuando alguien me cuenta sus problemas.",
    # Fila 4
    "No me preocupan especialmente las consecuencias que mis actos puedan tener sobre los demás.",
    # Fila 5
    "Estoy siempre informado sobre lo que sucede en el mundo.",
    # Fila 6
    "Nunca he dicho una mentira.",
    # Fila 7
    "No me gustan las actividades que exigen empeñarse y esforzarse hasta el agotamiento",
    # Fila 8
    "Tiendo a ser muy reflexivo.",
    # Fila 9
    "No suelo sentirme tenso.",
    # Fila 10
    "Noto fácilmente cuando las personas necesitan mi ayuda.",
    # Fila 11
    "No recuerdo fácilmente los números de teléfono.",
    # Fila 12
    "Siempre he estado completamente de acuerdo con los demás.",
    # Fila 13
    "Generalmente tiendo imponerme a las otras personas, más que ser complacientes con ellas.",
    # Fila 14
    "Ante los obstáculos grandes, no conviene empeñarse en conseguir los objetivos propios.",
    # Fila 15
    "Soy más bien susceptible.",
    # Fila 16
    "No es necesario comportarse cordialmente con todas las personas.",
    # Fila 17
    "No me siento muy atraído por las situaciones nuevas e inesperadas.",
    # Fila 18
    "Siempre he resuelto de inmediato todos los problemas que he encontrado.",
    # Fila 19
    "No me gustan los ambientes de trabajo en las que hay mucha competitividad.",
    # Fila 20
    "Llevo a cabo las decisiones que he tomado.",
    # Fila 21
    "No es fácil que algo o alguien me haga perder la paciencia.",
    # Fila 22
    "Me gusta mezclarme con la gente.",
    # Fila 23
    "Toda novedad me entusiasma.",
    # Fila 24
    "Nunca me he asustado ante un peligro, aunque fuera grave.",
    # Fila 25
    "Tiendo a decidir rápidamente.",
    # Fila 26
    "Antes de tomar cualquier iniciativa, me tomo tiempo para valorar las posibles consecuencias.",
    # Fila 27
    "No creo ser una persona ansiosa.",
    # Fila 28
    "No suelo saber cómo actuar ante las desgracias de mis amigos.",
    # Fila 29
    "Tengo muy buen memoria.",
    # Fila 30
    "Siempre he estado absolutamente seguro de todas mis acciones.",
    # Fila 31
    "En mi trabajo no le doy especial importancia a rendir mejor que los demás.",
    # Fila 32
    "No me gusta vivir de manera demasiado metódica y ordenada.",
    # Fila 33
    "Me siento vulnerable a las críticas de los demás.",
    # Fila 34
    "Si es preciso, no tengo inconveniente en ayudar a un desconocido.",
    # Fila 35
    "No me atraen las situaciones en constante cambio.",
    # Fila 36
    "Nunca he desobedecido las órdenes recibidas, ni siquiera siendo niño.",
    # Fila 37
    "No me gustan aquellas actividades en las que es preciso ir de un sitio a otro y moverse continuamente.",
    # Fila 38
    "No creo que sea preciso esforzarse más allá del límite de las propias fuerzas, incluso aunque haya que cumplir algún plazo.",
    # Fila 39
    "Estoy dispuesto a esforzarme al máximo con tal de destacar.",
    # Fila 40
    "Si tengo que criticar a los demás, lo hago, sobre todo cuando se lo merecen.",
    # Fila 41
    "Creo que no hay valores y costumbres totalmente válidos y eternos.",
    # Fila 42
    "Para enfrentarse a un problema no es efectivo tener presentes muchos puntos de vista diferentes.",
    # Fila 43
    "En general no me irrito, ni siquiera en situaciones en las que tendría motivos suficientes para ello.",
    # Fila 44
    "Si me equivoco, siempre me resulta fácil admitirlo.",
    # Fila 45
    "Cuando me enfado manifiesto mi malhumor.",
    # Fila 46
    "Llevo a cabo lo que he decidido, aunque me suponga un esfuerzo no previsto.",
    # Fila 47
    "No pierdo tiempo en aprender cosas que no estén estrictamente relacionadas con mi campo de intereses.",
    # Fila 48
    "Casi siempre sé cómo ajustarme a las exigencias de los demás.",
    # Fila 49
    "Llevo adelante las tareas emprendidas, aunque los resultados iniciales parezcan negativos.",
    # Fila 50
    "No suelo sentirme sólo y triste.",
    # Fila 51
    "No me gusta hacer varias cosas al mismo tiempo.",
    # Fila 52
    "Habitualmente muestro una actitud cordial, incluso con las personas que me provocan una cierta antipatía.",
    # Fila 53
    "A menudo estoy completamente absorbido por mis compromisos y actividades.",
    # Fila 54
    "Cuando algo entorpece mis proyectos, no insisto en conseguirlos e intento otros.",
    # Fila 55
    "No me interesan los programas de televisión que me exigen esfuerzo o compromiso.",
    # Fila 56
    "Soy una persona que siempre busca nuevas experiencias.",
    # Fila 57
    "Me molesta mucho el desorden.",
    # Fila 58
    "No suelo reaccionar de modo impulsivo.",
    # Fila 59
    "Siempre encuentro buenos argumentos para sostener mis propuestas y convencer a los demás de su validez.",
    # Fila 60
    "Me gusta estar bien informado, incluso sobre temas alejados de mi ámbito de competencia.",
    # Fila 61
    "No doy mucha importancia a demostrar mis capacidades.",
    # Fila 62
    "Mi humor pasa por altibajos frecuentes.",
    # Fila 63
    "A veces me enfado por cosas de poca importancia.",
    # Fila 64
    "No hago fácilmente un préstamo, ni siquiera a personas que conozco bien.",
    # Fila 65
    "No me gusta estar en grupos numerosos.",
    # Fila 66
    "No suelo planificar mi vida hasta en los más pequeños detalles.",
    # Fila 67
    "Nunca me han interesado la vida y costumbres de otros pueblos.",
    # Fila 68
    "No dudo en decir lo que pienso.",
    # Fila 69
    "A menudo me noto inquieto.",
    # Fila 70
    "En general no es conveniente mostrarse sensible a los problemas de los demás.",
    # Fila 71
    "En las reuniones no me preocupo especialmente por llamar la atención.",
    # Fila 72
    "Creo que todo problema puede ser resuelto de varias maneras.",
    # Fila 73
    "Si creo que tengo razón, intento convencer a los demás aunque me cueste tiempo y energía.",
    # Fila 74
    "Normalmente tiendo a no fiarme mucho de mi prójimo.",
    # Fila 75
    "Difícilmente desisto de una actividad que he comenzado.",
    # Fila 76
    "No suelo perder la calma.",
    # Fila 77
    "No dedico mucho tiempo a la lectura.",
    # Fila 78
    "Normalmente no entablo conversación con compañeros ocasionales de viaje.",
    # Fila 79
    "A veces soy tan escrupuloso que puedo resultar pesado.",
    # Fila 80
    "Siempre me he comportado de modo totalmente desinteresado.",
    # Fila 81
    "No tengo dificultad para controlar mis sentimientos.",
    # Fila 82
    "Nunca he sido un perfeccionista.",
    # Fila 83
    "En diversas circunstancias me he comportado impulsivamente.",
    # Fila 84
    "Nunca he discutido o peleado con otra persona.",
    # Fila 85
    "Es inútil empeñarse totalmente en algo, porque la perfección no se alcanza nunca.",
    # Fila 86
    "Tengo en gran consideración el punto de vista de mis compañeros.",
    # Fila 87
    "Siempre me han apasionado las ciencias.",
    # Fila 88
    "Me resulta fácil hacer confidencias a los demás.",
    # Fila 89
    "Normalmente no reacciono de modo exagerado, ni siquiera ante las emociones fuertes.",
    # Fila 90
    "No creo que conocer la historia sirva de mucho.",
    # Fila 91
    "No suelo reaccionar a las provocaciones.",
    # Fila 92
    "Nada de lo que he hecho podría haberlo hecho mejor.",
    # Fila 93
    "Creo que todas las personas tienen algo de bueno.",
    # Fila 94
    "Me resulta fácil hablar con personas que no conozco.",
    # Fila 95
    "No creo que haya posibilidad de convencer a otro cuando no piensa como nosotros.",
    # Fila 96
    "Si fracaso en algo, lo intento de nuevo hasta conseguirlo.",
    # Fila 97
    "Siempre me han fascinado las culturas muy diferentes a la mía.",
    # Fila 98
    "A menudo me siento nervioso.",
    # Fila 99
    "No soy una persona habladora.",
    # Fila 100
    "No merece mucho la pena ajustarse a las exigencias de los compañeros, cuando ello supone una disminución del propio ritmo de trabajo.",
    # Fila 101
    "Siempre he comprendido de inmediato todo lo que he leído.",
    # Fila 102
    "Siempre estoy seguro de mí mismo.",
    # Fila 103
    "No comprendo qué empuja a las personas a comportarse de modo diferente a la norma.",
    # Fila 104
    "Me molesta mucho que me interrumpan mientras estoy haciendo algo que me interesa.",
    # Fila 105
    "Me gusta mucho ver programas de información cultural o científica.",
    # Fila 106
    "Antes de entregar un trabajo, dedico mucho tiempo a revisarlo.",
    # Fila 107
    "Si algo no se desarrolla tan pronto como deseaba, no insisto demasiado.",
    # Fila 108
    "Si es preciso, no dudo en decir a las demás que se metan en sus asuntos.",
    # Fila 109
    "Si alguna acción mía puede llegar a desagradar a alguien, seguramente dejo de hacerla.",
    # Fila 110
    "Cuando un trabajo está terminado, no me pongo a repasarlo en sus mínimos detalles.",
    # Fila 111
    "Estoy convencido de que se obtienen mejores resultados cooperando con los demás, que compitiendo.",
    # Fila 112
    "Prefiero leer a practicar alguna actividad deportiva.",
    # Fila 113
    "Nunca he criticado a otra persona.",
    # Fila 114
    "Afronto todas mis actividades y experiencias con gran entusiasmo.",
    # Fila 115
    "Sólo quedo satisfecho cuando veo los resultados de lo que había programado.",
    # Fila 116
    "Cuando me critican, no puedo evitar exigir explicaciones.",
    # Fila 117
    "No se obtiene nada en la vida sin ser competitivo.",
    # Fila 118
    "Siempre intento ver las cosas desde distintos enfoques.",
    # Fila 119
    "Incluso en situaciones muy difíciles, no pierdo el control.",
    # Fila 120
    "A veces incluso pequeñas dificultades pueden llegar a preocuparme.",
    # Fila 121
    "Generalmente no me comporto de manera abierta con los extraños.",
    # Fila 122
    "No suelo cambiar de humor bruscamente.",
    # Fila 123
    "No me gustan las actividades que implican riesgo.",
    # Fila 124
    "Nunca he tenido mucho interés por los temas científicos o filosóficos.",
    # Fila 125
    "Cuando empiezo a hacer algo, nunca sé si lo terminaré.",
    # Fila 126
    "Generalmente confío en los demás y en sus intenciones.",
    # Fila 127
    "Siempre he mostrado simpatía por todas las personas que he conocido.",
    # Fila 128
    "Con ciertas personas no es necesario ser demasiado tolerante.",
    # Fila 129
    "Suelo cuidar todas las cosas hasta en sus mínimos detalles.",
    # Fila 130
    "No es trabajando en grupo como se pueden desarrollar mejor las propias capacidades.",
    # Fila 131
    "No suelo buscar soluciones nuevas a problemas para los que ya existe una solución eficaz.",
    # Fila 132
    "No creo que sea útil perder tiempo repasando varias veces el trabajo hecho.",
    ]
PREGUNTAS_COPE = [
    # Fila 1
    "Hago más de lo necesario con tal de superar el problema.",
    # Fila 2
    "Trato de encontrar cuáles son los pasos que tengo que hacer.",
    # Fila 3
    "Dejo todo de lado para dedicarme al problema.",
    # Fila 4
    "Me fuerzo a esperar el momento adecuado para actuar.",
    # Fila 5
    "Le pregunto a aquellos que han pasado por cosas parecidas, qué cosa hicieron.",
    # Fila 6
    "Le cuento a alguien cómo me siento.",
    # Fila 7
    "Trato de encontrar el lado bueno de lo que está pasando.",
    # Fila 8
    "Aprendo a vivir con el problema.",
    # Fila 9
    "Le pido a Dios que me ayude.",
    # Fila 10
    "Me molesto y expreso todo lo que siento.",
    # Fila 11
    "Me resisto a creer que eso haya pasado.",
    # Fila 12
    "Ya no hago ningún esfuerzo para conseguir lo que quiero.",
    # Fila 13
    "Me pongo a trabajar o a hacer cualquier cosa para no pensar en el asunto.",
    # Fila 14
    "Dedico todas mis fuerzas a hacer algo en relación al problema.",
    # Fila 15
    "Preparo un buen plan de acción.",
    # Fila 16
    "Me dedico totalmente a este asunto y, si hace falta, dejo de lado otras cosas.",
    # Fila 17
    "No hago nada hasta que la situación lo permita.",
    # Fila 18
    "Busco alguien que me aconseje qué tengo que hacer frente al problema.",
    # Fila 19
    "Busco amigos o parientes que me comprendan.",
    # Fila 20
    "Busco otras formas de entender el problema para que se vea más favorable.",
    # Fila 21
    "Acepto lo que pasó y que no puedo cambiarlo.",
    # Fila 22
    "Pongo mi confianza en Dios.",
    # Fila 23
    "Dejo salir todo lo que siento.",
    # Fila 24
    "Me hago la idea de que nada ha pasado.",
    # Fila 25
    "Dejo de insistir en conseguir lo que quería.",
    # Fila 26
    "Voy al cine o veo TV para no pensar tanto en el problema.",
    # Fila 27
    "Hago paso a paso lo que tiene que hacerse.",
    # Fila 28
    "Pienso bien qué pasos tengo que dar.",
    # Fila 29
    "Trato de no distraerme con otros pensamientos o actividades.",
    # Fila 30
    "Me aseguro de no empeorar las cosas por actuar precipitadamente.",
    # Fila 31
    "Hablo con quien puede darme mas informacion sobre la situacion",
    # Fila 32
    "Le cuento a alguien cómo me siento.",
    # Fila 33
    "Saco algún provecho de lo que me está pasando.",
    # Fila 34
    "Me hago a la idea de que el hecho ya se dio.",
    # Fila 35
    "Trato de encontrar consuelo en mi religión.",
    # Fila 36
    "Siento que me altero mucho y que expreso demasiado todo lo que siento.",
    # Fila 37
    "Hago como si no hubiera pasado nada.",
    # Fila 38
    "Reconozco que no puedo con el problema y ya no trato de resolverlo.",
    # Fila 39
    "Sueño despierto(a) sobre otras cosas diferentes al problema.",
    # Fila 40
    "Hago lo que tengo que hacer para darle vuelta al problema.",
    # Fila 41
    "Pienso cómo puedo manejar mejor el problema.",
    # Fila 42
    "Trato de evitar que otras cosas interfieran con mis esfuerzos para arreglar el asunto.",
    # Fila 43
    "Me controlo para no hacer las cosas apresuradamente.",
    # Fila 44
    "Hablo con quien pueda hacer algo concreto sobre el problema.",
    # Fila 45
    "Voy donde alguien que me acepte y me comprenda.",
    # Fila 46
    "Trato de que esa experiencia me sirva para madurar.",
    # Fila 47
    "Acepto la realidad de lo sucedido.",
    # Fila 48
    "Rezo más que de costumbre.",
    # Fila 49
    "Pierdo el control y me doy cuenta de ello.",
    # Fila 50
    "Me digo a mi mismo(a): “no puedo creer que esto me esté pasando”.",
    # Fila 51
    "Reduzco los esfuerzos que dedico a la solución del problema.",
    # Fila 52
    "Duermo más de lo acostumbrado."
]

class Command(BaseCommand):
    help = 'Carga las preguntas de los cuestionarios a la base de datos.'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando la carga de preguntas...')

        # Crear o encontrar los cuestionarios
        disc, _ = Cuestionario.objects.get_or_create(nombre='DISC')
        big_five, _ = Cuestionario.objects.get_or_create(nombre='BIG FIVE')
        cope, _ = Cuestionario.objects.get_or_create(nombre='COPE')

        # Función para cargar preguntas
        def cargar(cuestionario_obj, lista_preguntas):
            for i, texto_pregunta in enumerate(lista_preguntas):
                pregunta, created = Pregunta.objects.get_or_create(
                    texto=texto_pregunta,
                    defaults={'cuestionario': cuestionario_obj, 'orden': i + 1}
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  Creada: "{texto_pregunta[:40]}..."'))
                else:
                    self.stdout.write(f'  Ya existe: "{texto_pregunta[:40]}..."')

        # Ejecutar la carga
        self.stdout.write(f'\n--- Cargando {len(PREGUNTAS_DISC)} preguntas de DISC ---')
        cargar(disc, PREGUNTAS_DISC)
        self.stdout.write(f'\n--- Cargando {len(PREGUNTAS_BIG_FIVE)} preguntas de BIG FIVE ---')
        cargar(big_five, PREGUNTAS_BIG_FIVE)
        self.stdout.write(f'\n--- Cargando {len(PREGUNTAS_COPE)} preguntas de COPE ---')
        cargar(cope, PREGUNTAS_COPE)

        self.stdout.write(self.style.SUCCESS('\n¡Carga de preguntas completada!'))