import numpy as np
import time
import copy

class obj_reader(object):
    def __init__(self, filename, swapyz=False):
        """Loads a Wavefront OBJ file. """
        self.vertices = []
        self.normals = []
        self.texcoords = []
        self.faces = []
        self.mtl=None
        self.tmp = []
        material = None
        for line in open(filename, "r"):
            if line.startswith('#'): continue
            values = line.split()
            if not values: continue
            if values[0] == 'v':
                v=[ float(x) for x in values[1:4]]
                t = [ float(x) for x in values[4:]]
                if swapyz:
                    v = v[0], v[2], v[1]
                self.vertices.append(v)
                self.tmp.append(t)
            elif values[0] == 'vn':
                v=[ float(x) for x in values[1:4]]
                if swapyz:
                    v = v[0], v[2], v[1]
                self.normals.append(v)
            elif values[0] == 'vt':
                v = [float(x) for x in values[1:3]]
                self.texcoords.append(v)
            elif values[0] in ('usemtl', 'usemat'):
                material = values[1]
            elif values[0] == 'mtllib':
                self.mtl = [filename,values[1]]
            elif values[0] == 'f':
                face = []
                texcoords = []
                norms = []
                for v in values[1:]:
                    w = v.split('/')
                    face.append(int(w[0]))
                    if len(w) >= 2 and len(w[1]) > 0:
                        texcoords.append(int(w[1]))
                    else:
                        texcoords.append(0)
                    if len(w) >= 3 and len(w[2]) > 0:
                        norms.append(int(w[2]))
                    else:
                        norms.append(0)
                #self.faces.append((face, norms, texcoords, material))
                self.faces.append(line)

class FFD(object):

    def __init__(self,num_x,num_y,num_z,object_points,initial=True,cp_path=None):
        self.cp_num_x = num_x
        self.cp_num_y = num_y
        self.cp_num_z = num_z
        self.object_points = copy.deepcopy(object_points)
        self.initial = initial
        tmp = copy.deepcopy(object_points)
        tmp.sort(key=lambda x:x[0])
        self.min_x = tmp[0][0]
        self.max_x = tmp[-1][0]
        tmp.sort(key=lambda x: x[1])
        self.min_y = tmp[0][1]
        self.max_y = tmp[-1][1]
        tmp.sort(key=lambda x: x[2])
        self.min_z = tmp[0][2]
        self.max_z = tmp[-1][2]
        self.nx = (self.max_x - self.min_x) / (self.cp_num_x-1)
        self.ny = (self.max_y - self.min_y) / (self.cp_num_y-1)
        self.nz = (self.max_z - self.min_z) / (self.cp_num_z-1)
        self.changed = {}
        if self.initial:
            self.control_points = [
                [[np.array([0., 0., 0.])
                  for z in range(self.cp_num_z)]
                 for y in range(self.cp_num_y)]
                for x in range(self.cp_num_x)]
            self.control_points_location = [[[np.array([self.min_x+x*self.nx, self.min_y+y*self.ny, self.min_z+z*self.nz])
                  for z in range(self.cp_num_z)]
                 for y in range(self.cp_num_y)]
                for x in range(self.cp_num_x)]
        else:
            def load_cp(path):
                f = open(path,'r')
                begin = False
                while True:
                    line = f.readline()
                    if not begin:
                        if line.startswith('#'):
                            if '#dimension#' in line:
                                line = f.readline()
                                self.dimension = int(line.split('\n')[0])
                                continue
                            if '#offsets of the control points#' in line:
                                begin = True
                                x = 0
                                y = 0
                                continue
                            elif '#control grid size#' in line:
                                size = []
                                for i in range(self.dimension):
                                    line = f.readline()
                                    size.append(int(line.split('\n')[0]))
                                if self.dimension==3:
                                    control_points = [[[None for z in range(size[2])]
                                                       for y in range(size[1])]
                                                      for x in range(size[0])]
                                continue
                            else:
                                continue
                        else:
                            continue
                    else:
                        if line=='\n':
                            x += 1
                            y = 0
                            if x==size[0]:
                                break
                            else:
                                continue
                        else:
                            line = line.split('\t')[:-1]
                            for z in range(len(line)):
                                control_points[x][y][z] = line[z].split(' ')
                            y += 1
                return control_points
            self.control_points = load_cp(cp_path)
    def B(self,i, u):
        if i == 0:
            return (1 - u) ** 3 / 6
        elif i == 1:
            return (3 * u ** 3 - 6 * u ** 2 + 4) / 6
        elif i == 2:
            return (-3 * u ** 3 + 3 * u ** 2 + 3 * u + 1) / 6
        elif i == 3:
            return u ** 3 / 6

    def T_local(self,object_point):
        [x,y,z]= object_point
        i=int((x-self.min_x)/self.nx)-1
        j=int((y-self.min_y)/self.ny)-1
        k=int((z-self.min_z)/self.nz)-1
        u=(x-self.min_x)/self.nx-int((x-self.min_x)/self.nx)
        v=(y-self.min_y)/self.ny-int((y-self.min_y)/self.ny)
        w=(z-self.min_z)/self.nz-int((z-self.min_z)/self.nz)
        result = np.array([0.,0.,0.])
        for l in range(4):
            if 0<=i+l<self.cp_num_x:
                for m in range(4):
                    if 0<=j+m<self.cp_num_y:
                        for n in range(4):
                            if 0<=k+n<self.cp_num_z:
                                result += self.B(l, u) * self.B(m, v) * self.B(n, w) * \
                                          self.control_points[i + l][j + m][k + n]
        return result

    def changed_initial(self):
        self.changed = {}

    def changed_update(self,id,location):
        self.changed[id]=location

    # Change one control point, we will get the [u,v,w] of the control point.
    # def update_control_point(self, changed_control_point, change):
    #     [u, v, w] = changed_control_point
    #     self.control_points[u][v][w] += change
    #     self.control_points_location[u][v][w] += change
    #     for i in range(len(self.object_points)):
    #         self.object_points[i]=self.T_local(changed_control_point,self.object_points[i])
    #     return self.object_points

    def update_control_point(self):
        #tmp = copy.deepcopy(self.object_points)
        #result = []
        for (u,v,w), new_location in self.changed.items():
            self.control_points[u][v][w] = new_location-self.control_points_location[u][v][w]
        # for i in range(len(self.object_points)):
        #     change_point=self.T_local([u,v,w],tmp[i])
        #     if change_point[0]==0 and change_point[1]==0 and change_point[2]==0:
        #         continue
        #     else:
        #         result.append([i,self.object_points[i]+change_point])
        #return result

    def save_control_points(self,filename):
        f = open(filename,'w')
        f.write('#dimension#\n')
        f.write('3\n')
        f.write('#one to one#\n')
        f.write('1\n')
        f.write('#control grid size#\n')
        f.write(str(self.cp_num_x)+'\n')
        f.write(str(self.cp_num_y) + '\n')
        f.write(str(self.cp_num_z) + '\n')
        f.write('#control grid spacing#\n')
        f.write(str(self.nx) + '\n')
        f.write(str(self.ny) + '\n')
        f.write(str(self.nz) + '\n')
        f.write('#offsets of the control points#\n')
        for x in range(len(self.control_points)):
            for y in range(len(self.control_points[x])):
                for z in range(len(self.control_points[x][y])):
                    f.write(str(self.control_points[x][y][z][0])+' '+str(self.control_points[x][y][z][1])+' '+str(self.control_points[x][y][z][2])+'\t')
                f.write('\n')
            f.write('\n')
        f.write('#quaternion qf,qb,qc,qd,qx,qy,qz#\n')
        f.write('-1.000000	 0.000000	1.000000	0.000000	 90.000000	-126.000000	-72.000000')
        return


if __name__ == '__main__':
    start = time.clock()
    zxh = obj_reader('zxh-ape.obj')
    end = time.clock()
    print(end-start)
    start = time.clock()
    ffd = FFD(num_x=5,num_y=5,num_z=5,object_points=zxh.vertices)
    end = time.clock()
    print(end-start)
    start = time.clock()
    new_obj = ffd.update_control_point([1,1,1],np.array([-10000, 10000, 500]))
    end = time.clock()
    print(end-start)
    start = time.clock()
    ffd.save_control_points('temp.FFD')
    end = time.clock()
    print(end-start)
    start = time.clock()
    f = open('tmp.obj','w')
    for i in range(len(new_obj)):
        f.write('v '+str(new_obj[i][0])+' '+str(new_obj[i][1])+' '+str(new_obj[i][2])+' '+str(zxh.tmp[i][0])+' '+str(zxh.tmp[i][1])+' '+str(zxh.tmp[i][2])+'\n')
    for i in range(len(zxh.faces)):
        f.write(zxh.faces[i])
    f.close()
    end = time.clock()
    print(end-start)
