import shapefile
import pandas as pd
from shapely.geometry import Polygon
from shapely.ops import cascaded_union

class Cadastre(object):
    """docstring for Cadastre."""

    def __init__(self, file, index ='id'):
        super(Cadastre, self).__init__()
        self.file = file

        sf = shapefile.Reader(file)

        print('Loading: {}'.format(file))

        fields = [x[0] for x in sf.fields][1:]
        geom = pd.DataFrame(columns=fields, data=sf.records())
        geom = geom.assign(coords=[s.points for s in sf.shapes()])
        geom["coords"] = geom["coords"].apply(lambda x: Polygon([p for p in x]))

        geom.set_index(index, inplace = True)
        print('Loaded {} features'.format(geom.shape))
        self.geom = geom

    def get_section_geom(self):

        self.geom['section_id'] = [x[:10] for x in self.geom.index]
        geom_groups = self.geom.groupby(by = 'section_id')

        sections = []
        for name, group in geom_groups:
            sections.append({
                'section_id' : name,
                'section_coords' : cascaded_union([p.buffer(0) for p in group['coords']])
            })
        sections = pd.DataFrame(sections)
        sections.set_index('section_id', inplace = True)
        return sections

class ValeursFoncieres(object):
    """Charger et manipuler les données de valeurs foncières en Open Data"""

    def __init__(self, files, departements, paris = False):

        self.files = files

        dfs = []
        for f in files:
            print('Loading : {}'.format(f))
            temp = pd.read_csv(f, sep = '|')
            dfs.append(temp.loc[temp['Code departement'].isin(departements)])
            del temp
        df = pd.concat(dfs)

        df.dropna(subset = ["Valeur fonciere", "Code postal", 'Surface reelle bati'], inplace = True)

        df['Date mutation'] = pd.to_datetime(df['Date mutation'])
        df['Annee mutation'] = df['Date mutation'].dt.to_period('Y')
        df['Valeur fonciere'] = df['Valeur fonciere'].apply(lambda x: float(x.split(',')[:-1][0]))
        df['Code postal'] = df['Code postal'].apply(lambda x: str(int(x)))
        df['Section'] = df['Section'].apply(lambda x: x.zfill(5))
        df['No plan'] = df['No plan'].apply(lambda x: str(x).zfill(4))
        df['Id'] = df['Code postal'] + df['Section'] + df['No plan']
        df['prix m2'] = df['Valeur fonciere'] / df['Surface reelle bati']
        if paris:
            df['Id'] = df['Id'].apply(lambda x: '751' + x[3:])

        self.df = df
        print('Loaded {} DataFrame'.format(df.shape))

    def get_av_price_by_id(self):

        df_by_id = self.df.groupby(['Id'])

        av_price_by_id = df_by_id.mean()
        ntransacs_by_id = pd.Series(df_by_id.size(), name = 'ntransacs')
        av_price_by_id = av_price_by_id.join(ntransacs_by_id)
        av_price_by_id['section_id'] = [x[:10] for x in av_price_by_id.index]

        return av_price_by_id[["Surface reelle bati", 'prix m2', 'ntransacs', 'section_id']]
